"""Recorder controller: runs the capture -> VOX -> writer pipeline on a thread.

Owns the runtime state (idle / recording / paused) and exposes a tiny API the
tray and UI call: start(), stop(), pause(), resume(). Emits state changes via an
optional callback so the tray icon can reflect whether we're actively recording.
"""

from __future__ import annotations

import threading
from enum import Enum
from typing import Callable, Optional

from .config import MODE_CONTINUOUS, MODE_VOX, Settings
from .audio.capture import AudioCapture, CaptureError, estimate_ambient_rms
from .audio.dsp import DspChain
from .audio.vox import EventType, VoxEngine
from .audio.writer import SegmentWriter
from .postprocess import PostProcessor
from .scheduler import Schedule


class RecorderState(Enum):
    STOPPED = "stopped"
    LISTENING = "listening"   # armed, waiting for sound
    RECORDING = "recording"   # actively capturing a segment
    PAUSED = "paused"


class Recorder:
    def __init__(
        self,
        settings: Settings,
        on_state: Optional[Callable[[RecorderState], None]] = None,
        on_segment_complete=None,
    ):
        self.settings = settings
        self.on_state = on_state
        self.on_segment_complete = on_segment_complete

        self._post = PostProcessor.from_settings(settings)
        self._schedule = Schedule.from_config(getattr(settings, "schedule", None))

        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._state = RecorderState.STOPPED
        self.last_error: Optional[str] = None

    @property
    def state(self) -> RecorderState:
        return self._state

    def _set_state(self, state: RecorderState) -> None:
        if state is not self._state:
            self._state = state
            if self.on_state:
                self.on_state(state)

    # --- lifecycle ---
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._pause.clear()
        self._thread = threading.Thread(target=self._run, name="snoper-recorder", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._set_state(RecorderState.STOPPED)

    def pause(self) -> None:
        self._pause.set()
        self._set_state(RecorderState.PAUSED)

    def resume(self) -> None:
        self._pause.clear()
        self._set_state(RecorderState.LISTENING)

    @property
    def paused(self) -> bool:
        return self._pause.is_set()

    # --- worker ---
    def _build_engine(self) -> VoxEngine:
        threshold = self.settings.vox_threshold
        if self.settings.auto_calibrate:
            try:
                ambient = estimate_ambient_rms(self.settings)
                if ambient > 0:
                    threshold = max(
                        self.settings.vox_threshold,
                        ambient * self.settings.calibration_margin,
                    )
            except Exception:
                pass  # fall back to configured threshold
        # Continuous mode = always-on: a threshold of 0 keeps every frame "loud".
        if self.settings.mode == MODE_CONTINUOUS:
            threshold = 0.0
        return VoxEngine(
            threshold=threshold,
            frame_ms=self.settings.frame_ms,
            start_frames=self.settings.start_frames if self.settings.mode == MODE_VOX else 1,
            silence_timeout_s=self.settings.silence_timeout_s,
            preroll_ms=self.settings.preroll_ms,
        )

    def _segment_complete(self, path, started_at, duration_s) -> None:
        """Run post-processing, then hand the final file to the user callback."""
        final = self._post.run(path) if self._post.active else path
        if self.on_segment_complete:
            self.on_segment_complete(final, started_at, duration_s)

    def _run(self) -> None:
        try:
            engine = self._build_engine()
            dsp = DspChain(
                noise=getattr(self.settings, "noise_suppression", False),
                agc=self.settings.agc,
            )
            writer = SegmentWriter(self.settings, on_segment_complete=self._segment_complete)
            self._set_state(RecorderState.LISTENING)
            with AudioCapture(self.settings) as cap:
                for frame in cap.frames(self._stop):
                    # Schedule gate: outside configured windows, behave as paused.
                    if self._pause.is_set() or not self._schedule.is_active():
                        writer.handle(engine.flush())
                        continue
                    if dsp.active:
                        frame = dsp.process(frame)
                    events = engine.process(frame)
                    writer.handle(events)
                    for ev in events:
                        if ev.type is EventType.START:
                            self._set_state(RecorderState.RECORDING)
                        elif ev.type is EventType.STOP:
                            self._set_state(RecorderState.LISTENING)
                writer.handle(engine.flush())
            writer.close()
        except CaptureError as e:
            self.last_error = str(e)
            self._set_state(RecorderState.STOPPED)
        except Exception as e:  # pragma: no cover - defensive
            self.last_error = f"{type(e).__name__}: {e}"
            self._set_state(RecorderState.STOPPED)
