"""Segment writer: turns VOX events into timestamped audio files on disk.

Two layouts mirror the reference app's modes:
  - Per-segment files (VOX / continuous): one WAV per detected segment.
  - Dictation: a single growing WAV with a sidecar of segment timestamps.

Pure file/buffer handling; the capture loop feeds it VoxEvents. Uses `soundfile`
when available, otherwise falls back to the stdlib `wave` module so the core works
without extra deps during development.
"""

from __future__ import annotations

import json
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

from ..config import MODE_DICTATION, Settings
from .vox import EventType, VoxEvent

try:
    import soundfile as _sf  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    _sf = None


def _to_int16(frame: np.ndarray) -> np.ndarray:
    clipped = np.clip(frame, -1.0, 1.0)
    return (clipped * 32767.0).astype(np.int16)


class _WavFile:
    """Thin wrapper writing float32 frames as 16-bit PCM WAV."""

    def __init__(self, path: Path, samplerate: int, channels: int):
        self.path = path
        self._wav = wave.open(str(path), "wb")
        self._wav.setnchannels(channels)
        self._wav.setsampwidth(2)
        self._wav.setframerate(samplerate)
        self.frames_written = 0

    def write(self, frame: np.ndarray) -> None:
        pcm = _to_int16(frame)
        self._wav.writeframes(pcm.tobytes())
        self.frames_written += len(frame)

    def close(self) -> None:
        self._wav.close()


class SegmentWriter:
    """Consumes VoxEvents and produces audio files.

    Call `handle(events)` with the list returned by VoxEngine.process(), and
    `close()` on shutdown. `on_segment_complete(path, started_at, duration_s)` is
    invoked whenever a segment file is finalized (used to queue transcription).
    """

    def __init__(self, settings: Settings, on_segment_complete=None):
        self.settings = settings
        self.on_segment_complete = on_segment_complete
        self.out_dir = Path(settings.recordings_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self._current: _WavFile | None = None
        self._seg_started: datetime | None = None
        self._seg_samples = 0

        # Dictation mode: one continuous file + timestamp index.
        self._dictation = settings.mode == MODE_DICTATION
        self._dict_file: _WavFile | None = None
        self._dict_marks: list[dict] = []
        self._dict_path: Path | None = None

    # --- naming ---
    def _timestamp_name(self, when: datetime, ext: str) -> Path:
        return self.out_dir / f"{when:%Y%m%d_%H%M%S}.{ext}"

    def _ensure_dictation_file(self) -> _WavFile:
        if self._dict_file is None:
            now = datetime.now()
            self._dict_path = self._timestamp_name(now, "wav")
            self._dict_file = _WavFile(
                self._dict_path, self.settings.samplerate, self.settings.channels
            )
        return self._dict_file

    # --- event handling ---
    def handle(self, events: list[VoxEvent]) -> None:
        for ev in events:
            if ev.type is EventType.START:
                self._start_segment(ev)
            elif ev.type is EventType.FRAME:
                self._write_frame(ev.frame)
            elif ev.type is EventType.STOP:
                self._stop_segment()

    def _start_segment(self, ev: VoxEvent) -> None:
        self._seg_started = datetime.now()
        self._seg_samples = 0
        if self._dictation:
            f = self._ensure_dictation_file()
            self._dict_marks.append(
                {"start_sample": f.frames_written, "start_time": self._seg_started.isoformat()}
            )
        else:
            self._current = _WavFile(
                self._timestamp_name(self._seg_started, "wav"),
                self.settings.samplerate,
                self.settings.channels,
            )
        for frame in ev.preroll or []:
            self._write_frame(frame)

    def _write_frame(self, frame) -> None:
        if frame is None:
            return
        target = self._dict_file if self._dictation else self._current
        if target is None:
            return
        target.write(frame)
        self._seg_samples += len(frame)

    def _stop_segment(self) -> None:
        if self._seg_started is None:
            return
        duration = self._seg_samples / self.settings.samplerate
        too_short = duration < self.settings.min_segment_s

        if self._dictation:
            if self._dict_marks:
                self._dict_marks[-1]["duration_s"] = round(duration, 3)
                self._flush_dictation_index()
            if not too_short and self.on_segment_complete and self._dict_path:
                self.on_segment_complete(self._dict_path, self._seg_started, duration)
        else:
            if self._current is not None:
                path = self._current.path
                self._current.close()
                self._current = None
                if too_short:
                    path.unlink(missing_ok=True)
                elif self.on_segment_complete:
                    self.on_segment_complete(path, self._seg_started, duration)

        self._seg_started = None
        self._seg_samples = 0

    def _flush_dictation_index(self) -> None:
        if self._dict_path is None:
            return
        idx = self._dict_path.with_suffix(".segments.json")
        idx.write_text(json.dumps(self._dict_marks, indent=2))

    def close(self) -> None:
        self._stop_segment()
        if self._dict_file is not None:
            self._dict_file.close()
            self._dict_file = None
            self._flush_dictation_index()
