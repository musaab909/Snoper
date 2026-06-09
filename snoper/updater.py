"""Auto-update via GitHub Releases.

Flow:
  1. check() asks the GitHub Releases API for the latest published release.
  2. If its version tag is newer than the running version, it returns an
     UpdateInfo with the installer asset's download URL.
  3. download() fetches the installer to a temp file.
  4. install() launches the installer **silently** and exits the app so the
     installer can replace the running exe; the new version starts afterward.

Only meaningful for the packaged Windows build (frozen exe). In dev/source mode
it checks but install() is a no-op (nothing to replace).

No third-party deps: uses urllib. For a private repo, set a token in settings
(`update_token`) or the GITHUB_TOKEN env var so the API + asset download authorize.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from typing import Optional

from .version import GITHUB_REPO, __version__


@dataclass
class UpdateInfo:
    version: str
    download_url: str
    asset_name: str
    notes: str = ""


def parse_version(v: str):
    """'v1.2.3' / '1.2.3' -> (1, 2, 3). Non-numeric tails are ignored."""
    nums = re.findall(r"\d+", v or "")
    return tuple(int(n) for n in nums[:3]) or (0,)


def is_newer(remote: str, local: str) -> bool:
    return parse_version(remote) > parse_version(local)


def _request(url: str, token: Optional[str], accept: str) -> urllib.request.Request:
    req = urllib.request.Request(url)
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "Snoper-Updater")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return req


def _token(settings) -> Optional[str]:
    return (
        getattr(settings, "update_token", None)
        or os.environ.get("GITHUB_TOKEN")
        or None
    )


def check(settings, repo: str = GITHUB_REPO) -> Optional[UpdateInfo]:
    """Return UpdateInfo if a newer release exists, else None."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    token = _token(settings)
    ctx = ssl.create_default_context()
    try:
        req = _request(url, token, "application/vnd.github+json")
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.load(resp)
    except Exception as e:
        print(f"[snoper] update check failed: {e}")
        return None

    tag = data.get("tag_name", "")
    if not tag or not is_newer(tag, __version__):
        return None

    # Prefer the installer asset (.exe with 'Setup' in the name), else first .exe.
    assets = data.get("assets", [])
    asset = next(
        (a for a in assets if a["name"].lower().endswith(".exe") and "setup" in a["name"].lower()),
        next((a for a in assets if a["name"].lower().endswith(".exe")), None),
    )
    if not asset:
        return None

    # For private repos the API asset URL (not browser_download_url) authorizes via token.
    dl = asset["url"] if token else asset.get("browser_download_url", asset["url"])
    return UpdateInfo(
        version=tag,
        download_url=dl,
        asset_name=asset["name"],
        notes=data.get("body", "") or "",
    )


def download(info: UpdateInfo, settings) -> Optional[str]:
    """Download the installer to a temp file; return its path."""
    token = _token(settings)
    # Asset API URL needs the octet-stream Accept header to get binary content.
    accept = "application/octet-stream" if "/assets/" in info.download_url else "*/*"
    ctx = ssl.create_default_context()
    dest = os.path.join(tempfile.gettempdir(), info.asset_name)
    try:
        req = _request(info.download_url, token, accept)
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp, open(dest, "wb") as f:
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
        return dest
    except Exception as e:
        print(f"[snoper] update download failed: {e}")
        return None


def install(installer_path: str) -> bool:
    """Launch the installer silently and signal the app to exit.

    Inno Setup flags: /VERYSILENT no UI, /SUPPRESSMSGBOXES, /NORESTART, and
    /CLOSEAPPLICATIONS so it can replace the running exe. The installer keeps the
    same AppId, so it upgrades in place; it relaunches Snoper via the [Run] step.
    """
    if os.name != "nt" or not getattr(sys, "frozen", False):
        print("[snoper] install skipped (only applies to the packaged Windows exe)")
        return False
    try:
        subprocess.Popen(
            [installer_path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
            close_fds=True,
        )
        return True
    except Exception as e:
        print(f"[snoper] failed to launch installer: {e}")
        return False


def check_and_update(settings, on_status=None) -> bool:
    """Convenience: check -> download -> install. Returns True if updating.

    `on_status(msg)` receives short progress strings for the tray/UI.
    """
    def status(msg):
        if on_status:
            on_status(msg)

    info = check(settings)
    if not info:
        status("Up to date")
        return False
    status(f"Downloading update {info.version}…")
    path = download(info, settings)
    if not path:
        status("Update download failed")
        return False
    status(f"Installing {info.version}…")
    if install(path):
        return True
    status("Update ready — run the downloaded installer to finish")
    return False
