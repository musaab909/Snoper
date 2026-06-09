"""Spectrum analyzer: FFT magnitude + log-spaced frequency bands.

Used for the live spectrum view and for helping tune the VOX threshold. Pure
numpy; feed it frames and read back band magnitudes or the dominant frequency.
"""

from __future__ import annotations

import numpy as np


class SpectrumAnalyzer:
    def __init__(self, samplerate: int, n_bands: int = 24, fmin: float = 50.0, fmax: float | None = None):
        self.samplerate = samplerate
        self.n_bands = n_bands
        self.fmin = fmin
        self.fmax = fmax or samplerate / 2
        self._edges = np.logspace(np.log10(self.fmin), np.log10(self.fmax), n_bands + 1)

    def magnitude_spectrum(self, frame: np.ndarray):
        """Return (freqs, magnitudes) for a single frame using a Hann window."""
        if len(frame) == 0:
            return np.array([]), np.array([])
        windowed = frame * np.hanning(len(frame))
        spec = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(len(frame), d=1.0 / self.samplerate)
        return freqs, spec

    def bands(self, frame: np.ndarray) -> np.ndarray:
        """Aggregate magnitude into log-spaced bands (mean per band)."""
        freqs, mag = self.magnitude_spectrum(frame)
        if len(freqs) == 0:
            return np.zeros(self.n_bands)
        out = np.zeros(self.n_bands)
        idx = np.digitize(freqs, self._edges) - 1
        for b in range(self.n_bands):
            sel = mag[idx == b]
            out[b] = sel.mean() if sel.size else 0.0
        return out

    def dominant_frequency(self, frame: np.ndarray) -> float:
        freqs, mag = self.magnitude_spectrum(frame)
        if len(freqs) == 0:
            return 0.0
        return float(freqs[int(np.argmax(mag))])

    def band_edges(self) -> np.ndarray:
        return self._edges
