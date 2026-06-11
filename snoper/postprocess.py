"""Post-processing pipeline applied when a recording segment is finalized.

Each step is a small plugin run in order; failures are logged and don't break the
chain. Configured from Settings. Steps:
  - CompressMp3: re-encode WAV -> MP3 via ffmpeg (if available), optionally delete WAV.
  - Encrypt: AES-encrypt the file with a passphrase-derived key (Fernet).
  - CloudUpload: copy to a destination dir, or upload via Dropbox/FTP if configured.
  - EmailDelivery: send the file as an attachment via SMTP.

All external integrations degrade gracefully if their dependency/credentials are
absent — the step is skipped with a logged note rather than crashing the recorder.
"""

from __future__ import annotations

import logging
import shutil
import smtplib
import subprocess
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

log = logging.getLogger("snoper.postprocess")


class Step(Protocol):
    def run(self, path: Path) -> Path: ...


def _have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


class CompressMp3:
    def __init__(self, bitrate: str = "128k", delete_source: bool = True):
        self.bitrate = bitrate
        self.delete_source = delete_source

    def run(self, path: Path) -> Path:
        if path.suffix.lower() == ".mp3" or not _have_ffmpeg():
            return path
        out = path.with_suffix(".mp3")
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(path), "-b:a", self.bitrate, str(out)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if self.delete_source:
            path.unlink(missing_ok=True)
        return out


class Encrypt:
    """AES encryption via cryptography.Fernet; writes `<name>.enc`, removes plaintext."""

    def __init__(self, passphrase: str, delete_source: bool = True):
        self.passphrase = passphrase
        self.delete_source = delete_source

    def _key(self):
        import base64
        import hashlib

        digest = hashlib.sha256(self.passphrase.encode()).digest()
        return base64.urlsafe_b64encode(digest)

    def run(self, path: Path) -> Path:
        try:
            from cryptography.fernet import Fernet  # type: ignore
        except Exception:
            log.warning("encryption skipped: pip install cryptography")
            return path
        token = Fernet(self._key()).encrypt(path.read_bytes())
        out = path.with_suffix(path.suffix + ".enc")
        out.write_bytes(token)
        if self.delete_source:
            path.unlink(missing_ok=True)
        return out


class CloudUpload:
    """Copy to a destination folder (e.g. a synced Dropbox dir) or FTP upload."""

    def __init__(self, dest_dir: str | None = None, ftp: dict | None = None):
        self.dest_dir = dest_dir
        self.ftp = ftp

    def run(self, path: Path) -> Path:
        if self.dest_dir:
            dest = Path(self.dest_dir)
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest / path.name)
        if self.ftp:
            self._ftp_upload(path)
        return path

    def _ftp_upload(self, path: Path) -> None:
        try:
            from ftplib import FTP

            with FTP(self.ftp["host"]) as ftp:
                ftp.login(self.ftp.get("user", ""), self.ftp.get("password", ""))
                if self.ftp.get("dir"):
                    ftp.cwd(self.ftp["dir"])
                with open(path, "rb") as f:
                    ftp.storbinary(f"STOR {path.name}", f)
        except Exception as e:
            log.warning("FTP upload failed: %s", e)


class EmailDelivery:
    def __init__(self, smtp: dict):
        self.smtp = smtp  # {host, port, user, password, to, from}

    def run(self, path: Path) -> Path:
        try:
            msg = EmailMessage()
            msg["Subject"] = f"Snoper recording: {path.name}"
            msg["From"] = self.smtp["from"]
            msg["To"] = self.smtp["to"]
            msg.set_content("Attached recording from Snoper.")
            msg.add_attachment(
                path.read_bytes(), maintype="audio", subtype="mpeg", filename=path.name
            )
            with smtplib.SMTP(self.smtp["host"], self.smtp.get("port", 587)) as s:
                s.starttls()
                s.login(self.smtp["user"], self.smtp["password"])
                s.send_message(msg)
        except Exception as e:
            log.warning("email delivery failed: %s", e)
        return path


class PostProcessor:
    """Runs configured steps in order on each finalized recording.

    Build from Settings via `from_settings`. Steps that fail log and are skipped;
    the chain continues with whatever path the previous step returned.
    """

    def __init__(self, steps: list[Step] | None = None):
        self.steps: list[Step] = steps or []

    @classmethod
    def from_settings(cls, settings) -> PostProcessor:
        steps: list[Step] = []
        pp = getattr(settings, "postprocess", None) or {}
        if pp.get("mp3"):
            steps.append(
                CompressMp3(
                    bitrate=pp.get("mp3_bitrate", "128k"),
                    delete_source=pp.get("mp3_delete_source", True),
                )
            )
        if pp.get("encrypt_passphrase"):
            steps.append(Encrypt(pp["encrypt_passphrase"]))
        if pp.get("cloud_dir") or pp.get("ftp"):
            steps.append(CloudUpload(dest_dir=pp.get("cloud_dir"), ftp=pp.get("ftp")))
        if pp.get("smtp"):
            steps.append(EmailDelivery(pp["smtp"]))
        return cls(steps)

    @property
    def active(self) -> bool:
        return bool(self.steps)

    def run(self, path: Path) -> Path:
        current = Path(path)
        for step in self.steps:
            try:
                current = step.run(current)
            except Exception as e:
                log.warning("post-process step %s failed: %s", type(step).__name__, e)
        return current
