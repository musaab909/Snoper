"""Audio capture: device enumeration and a frame-yielding input stream.

Wraps `sounddevice` (PortAudio). Yields fixed-size float32 frames sized to the
VOX frame length. On Windows it can open a WASAPI loopback stream to capture
system audio (remote meeting participants); on other platforms loopback is a
no-op and only the microphone is captured.
"""

from __future__ import annotations

import queue
from typing import Iterator, List, Optional

import numpy as np

from ..config import Settings

try:
    import sounddevice as _sd  # type: ignore
except Exception:  # pragma: no cover - hardware/optional dependency
    _sd = None


class CaptureError(RuntimeError):
    pass


def list_input_devices() -> List[dict]:
    """Return available input devices as [{index, name, channels, default}]."""
    if _sd is None:
        return []
    devices = []
    default_in = None
    try:
        default_in = _sd.default.device[0]
    except Exception:
        pass
    for i, dev in enumerate(_sd.query_devices()):
        if dev.get("max_input_channels", 0) > 0:
            devices.append(
                {
                    "index": i,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "default": i == default_in,
                }
            )
    return devices


def _wasapi_loopback_settings():
    """Extra settings to capture system audio on Windows; None elsewhere."""
    if _sd is None or not hasattr(_sd, "WasapiSettings"):
        return None
    try:
        return _sd.WasapiSettings(loopback=True)
    except TypeError:
        # Older sounddevice without loopback support.
        return None


class AudioCapture:
    """Context manager yielding VOX-sized frames from an input stream."""

    def __init__(self, settings: Settings):
        if _sd is None:
            raise CaptureError(
                "sounddevice is not installed. Install with: pip install sounddevice"
            )
        self.settings = settings
        self._q: "queue.Queue[np.ndarray]" = queue.Queue()
        self._stream: Optional["_sd.InputStream"] = None
        self._frame_samples = settings.frame_samples

    def _callback(self, indata, frames, time_info, status):  # pragma: no cover - realtime
        # Mix to mono and enqueue a copy; never block the audio thread.
        mono = indata.mean(axis=1) if indata.ndim > 1 else indata
        self._q.put(mono.copy())

    def __enter__(self) -> "AudioCapture":
        extra = None
        if self.settings.capture_system_audio:
            extra = _wasapi_loopback_settings()
        self._stream = _sd.InputStream(
            samplerate=self.settings.samplerate,
            channels=self.settings.channels,
            dtype="float32",
            blocksize=self._frame_samples,
            device=self.settings.input_device,
            callback=self._callback,
            extra_settings=extra,
        )
        self._stream.start()
        return self

    def frames(self, stop_event) -> Iterator[np.ndarray]:
        """Yield exactly frame_samples-long frames until stop_event is set."""
        buf = np.empty(0, dtype=np.float32)
        n = self._frame_samples
        while not stop_event.is_set():
            try:
                chunk = self._q.get(timeout=0.25)
            except queue.Empty:
                continue
            buf = np.concatenate([buf, chunk])
            while len(buf) >= n:
                yield buf[:n]
                buf = buf[n:]

    def __exit__(self, *exc) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


def estimate_ambient_rms(settings: Settings, seconds: float = 1.0) -> float:
    """Sample ambient noise to auto-calibrate the VOX threshold."""
    from .vox import rms

    if _sd is None:
        return 0.0
    frames = int(settings.samplerate * seconds)
    rec = _sd.rec(
        frames,
        samplerate=settings.samplerate,
        channels=1,
        dtype="float32",
        device=settings.input_device,
    )
    _sd.wait()
    return rms(rec.flatten())
