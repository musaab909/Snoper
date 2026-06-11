"""Signal processing applied to captured frames: noise suppression + AGC.

All pure-numpy and stateful-per-stream so it can run inline in the capture loop
before frames reach the VOX engine and writer.

- NoiseSuppressor: spectral-subtraction gate. Learns a noise floor magnitude
  spectrum from the first frames (assumed near-silence / ambient) and subtracts
  it, attenuating bins dominated by noise.
- AutomaticGainControl: smoothly scales frame amplitude toward a target RMS so
  quiet sources become audible without clipping loud ones.
"""

from __future__ import annotations

import numpy as np


class NoiseSuppressor:
    """Spectral-subtraction noise gate.

    Args:
        learn_frames: number of initial frames used to estimate the noise profile.
        over_subtraction: factor multiplying the noise estimate (>1 = more aggressive).
        floor: residual gain floor so suppressed bins aren't fully zeroed (musical noise).
    """

    def __init__(self, learn_frames: int = 20, over_subtraction: float = 1.5, floor: float = 0.05):
        self.learn_frames = max(1, learn_frames)
        self.over_subtraction = over_subtraction
        self.floor = floor
        self._noise_mag: np.ndarray | None = None
        self._learned = 0

    @property
    def ready(self) -> bool:
        return self._noise_mag is not None and self._learned >= self.learn_frames

    def process(self, frame: np.ndarray) -> np.ndarray:
        if len(frame) == 0:
            return frame
        spec = np.fft.rfft(frame)
        mag = np.abs(spec)
        phase = np.angle(spec)

        if self._learned < self.learn_frames:
            # accumulate running mean of magnitude as the noise estimate
            if self._noise_mag is None:
                self._noise_mag = mag.copy()
            else:
                self._noise_mag = (self._noise_mag * self._learned + mag) / (self._learned + 1)
            self._learned += 1
            return frame  # pass through while learning

        assert self._noise_mag is not None  # always set by the learning phase above
        clean_mag = mag - self.over_subtraction * self._noise_mag
        clean_mag = np.maximum(clean_mag, self.floor * mag)
        cleaned = np.fft.irfft(clean_mag * np.exp(1j * phase), n=len(frame))
        return cleaned.astype(np.float32)


class AutomaticGainControl:
    """Smooth RMS-targeting gain with attack/release and a max-gain cap."""

    def __init__(self, target_rms: float = 0.1, max_gain: float = 8.0, smoothing: float = 0.9):
        self.target_rms = target_rms
        self.max_gain = max_gain
        self.smoothing = smoothing
        self._gain = 1.0

    def process(self, frame: np.ndarray) -> np.ndarray:
        if len(frame) == 0:
            return frame
        rms = float(np.sqrt(np.mean(np.square(frame, dtype=np.float64))))
        if rms > 1e-6:
            desired = min(self.max_gain, self.target_rms / rms)
        else:
            desired = self._gain  # silence: hold gain
        # exponential smoothing toward desired gain
        self._gain = self.smoothing * self._gain + (1 - self.smoothing) * desired
        out = frame * self._gain
        return np.clip(out, -1.0, 1.0).astype(np.float32)


class DspChain:
    """Optional noise suppression then AGC, configured from Settings."""

    def __init__(self, noise: bool = False, agc: bool = False):
        self._ns = NoiseSuppressor() if noise else None
        self._agc = AutomaticGainControl() if agc else None

    def process(self, frame: np.ndarray) -> np.ndarray:
        if self._ns is not None:
            frame = self._ns.process(frame)
        if self._agc is not None:
            frame = self._agc.process(frame)
        return frame

    @property
    def active(self) -> bool:
        return self._ns is not None or self._agc is not None
