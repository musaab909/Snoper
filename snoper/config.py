"""Settings load/save for Snoper.

Settings persist as JSON in the user's config directory. All recording behavior
(VOX threshold, silence timeout, recording mode, transcription, autostart) is
driven from here so the rest of the app stays stateless about configuration.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


def _default_recordings_dir() -> str:
    return str(Path.home() / "Snoper" / "Recordings")


def _config_path() -> Path:
    """Platform-appropriate config file path."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "Snoper" / "config.json"


# Recording modes mirror the reference app: VOX, dictation (one file), continuous.
MODE_VOX = "vox"
MODE_DICTATION = "dictation"
MODE_CONTINUOUS = "continuous"
VALID_MODES = (MODE_VOX, MODE_DICTATION, MODE_CONTINUOUS)


@dataclass
class Settings:
    # --- Audio capture ---
    samplerate: int = 16000          # 16 kHz is plenty for speech + Whisper
    channels: int = 1
    frame_ms: int = 30               # VOX analysis frame size
    input_device: Optional[int] = None       # None = system default
    capture_system_audio: bool = False        # Windows WASAPI loopback

    # --- VOX engine ---
    mode: str = MODE_VOX
    vox_threshold: float = 0.02      # RMS (0..1); auto-calibrated on first run if enabled
    auto_calibrate: bool = True
    calibration_margin: float = 3.0  # threshold = ambient_rms * margin
    start_frames: int = 3            # consecutive loud frames to start
    silence_timeout_s: float = 2.0   # silence before stopping a segment
    preroll_ms: int = 300            # audio kept before trigger so 1st syllable survives
    agc: bool = False                # automatic gain control for low-amplitude sound
    noise_suppression: bool = False  # spectral-subtraction noise gate

    # --- Output ---
    recordings_dir: str = field(default_factory=_default_recordings_dir)
    file_format: str = "wav"         # wav | mp3 (mp3 needs ffmpeg)
    min_segment_s: float = 0.5       # discard sub-half-second blips

    # --- Transcription ---
    transcribe: bool = False
    whisper_model: str = "base"      # tiny|base|small|medium|large
    whisper_language: Optional[str] = None   # None = auto-detect

    # --- App ---
    autostart: bool = False
    paused: bool = False
    # Visible recording indicator is always on by design; no stealth/hidden mode.

    # --- Scheduling: list of {start: "HH:MM", end: "HH:MM", days: [0..6]} ---
    # Empty list = record 24/7. See snoper.scheduler.Schedule.
    schedule: list = field(default_factory=list)

    # --- Post-processing on each finalized recording ---
    # Keys: mp3, mp3_bitrate, mp3_delete_source, encrypt_passphrase,
    #       cloud_dir, ftp{host,user,password,dir}, smtp{host,port,user,password,to,from}
    postprocess: dict = field(default_factory=dict)

    def validate(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(f"invalid mode {self.mode!r}, expected one of {VALID_MODES}")
        if self.frame_ms <= 0:
            raise ValueError("frame_ms must be > 0")
        if not (0.0 <= self.vox_threshold <= 1.0):
            raise ValueError("vox_threshold must be in [0, 1]")
        if self.start_frames < 1:
            raise ValueError("start_frames must be >= 1")
        if self.silence_timeout_s < 0:
            raise ValueError("silence_timeout_s must be >= 0")

    @property
    def frame_samples(self) -> int:
        return int(self.samplerate * self.frame_ms / 1000)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Settings":
        path = path or _config_path()
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        settings = cls(**filtered)
        settings.validate()
        return settings

    def save(self, path: Optional[Path] = None) -> None:
        path = path or _config_path()
        self.validate()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))
