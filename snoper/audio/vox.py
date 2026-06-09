"""Voice-activated (VOX) detection state machine.

Pure logic: feed it fixed-size audio frames (float32 numpy arrays in [-1, 1]) and
it tells you when a recording segment starts and ends. No I/O, no threads — that
keeps it deterministic and unit-testable with synthetic frames.

Behavior:
  - A segment STARTS after `start_frames` consecutive frames above threshold.
  - Once started, a `preroll` of recently-buffered frames is prepended so the first
    syllable isn't clipped.
  - A segment ENDS after `silence_timeout` of continuous sub-threshold audio.
  - Hysteresis (start_frames + silence_timeout) prevents rapid on/off flicker and
    keeps natural pauses inside one segment.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import numpy as np


class VoxState(Enum):
    IDLE = "idle"
    RECORDING = "recording"


class EventType(Enum):
    START = "start"      # segment opened; `preroll` holds buffered lead-in frames
    FRAME = "frame"      # a frame belonging to the open segment
    STOP = "stop"        # segment closed


@dataclass
class VoxEvent:
    type: EventType
    frame: Optional[np.ndarray] = None
    preroll: Optional[List[np.ndarray]] = None


def rms(frame: np.ndarray) -> float:
    """Root-mean-square energy of a frame, robust to empty input."""
    if frame is None or len(frame) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(frame, dtype=np.float64))))


class VoxEngine:
    """Frame-driven VOX state machine.

    Args:
        threshold: RMS level above which a frame counts as "loud".
        frame_ms: duration of each frame (for converting time settings to counts).
        start_frames: consecutive loud frames required to open a segment.
        silence_timeout_s: silence duration that closes an open segment.
        preroll_ms: amount of pre-trigger audio to retain.
    """

    def __init__(
        self,
        threshold: float,
        frame_ms: int,
        start_frames: int = 3,
        silence_timeout_s: float = 2.0,
        preroll_ms: int = 300,
    ):
        self.threshold = threshold
        self.frame_ms = frame_ms
        self.start_frames = max(1, start_frames)
        self.silence_frames = max(0, math.ceil(silence_timeout_s * 1000 / frame_ms))
        preroll_count = max(0, round(preroll_ms / frame_ms))

        self.state = VoxState.IDLE
        self._loud_run = 0
        self._silence_run = 0
        self._preroll: deque = deque(maxlen=preroll_count)

    def is_loud(self, frame: np.ndarray) -> bool:
        return rms(frame) >= self.threshold

    def process(self, frame: np.ndarray) -> List[VoxEvent]:
        """Feed one frame; return zero or more events to act on."""
        loud = self.is_loud(frame)
        events: List[VoxEvent] = []

        if self.state is VoxState.IDLE:
            self._preroll.append(frame)
            if loud:
                self._loud_run += 1
                if self._loud_run >= self.start_frames:
                    preroll = list(self._preroll)
                    self._preroll.clear()
                    self.state = VoxState.RECORDING
                    self._loud_run = 0
                    self._silence_run = 0
                    events.append(VoxEvent(EventType.START, preroll=preroll))
            else:
                self._loud_run = 0
        else:  # RECORDING
            events.append(VoxEvent(EventType.FRAME, frame=frame))
            if loud:
                self._silence_run = 0
            else:
                self._silence_run += 1
                if self._silence_run > self.silence_frames:
                    self.state = VoxState.IDLE
                    self._silence_run = 0
                    events.append(VoxEvent(EventType.STOP))

    # `events` already contains START's preroll frames; the writer is responsible
    # for emitting them before subsequent FRAME events.
        return events

    def flush(self) -> List[VoxEvent]:
        """Close any open segment (e.g. on shutdown or pause)."""
        if self.state is VoxState.RECORDING:
            self.state = VoxState.IDLE
            self._silence_run = 0
            return [VoxEvent(EventType.STOP)]
        return []
