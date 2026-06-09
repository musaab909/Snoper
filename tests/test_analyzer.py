"""Tests for the spectrum analyzer."""

import numpy as np

from snoper.audio.analyzer import SpectrumAnalyzer


def _tone(freq, sr=16000, n=2048):
    t = np.arange(n) / sr
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def test_dominant_frequency_detects_tone():
    sa = SpectrumAnalyzer(samplerate=16000)
    f = sa.dominant_frequency(_tone(1000))
    assert abs(f - 1000) < 30  # within one FFT bin's tolerance


def test_bands_shape_and_energy_location():
    sa = SpectrumAnalyzer(samplerate=16000, n_bands=24)
    bands = sa.bands(_tone(1000))
    assert bands.shape == (24,)
    assert bands.argmax() > 0  # energy not in the lowest band for a 1kHz tone


def test_empty_frame_safe():
    sa = SpectrumAnalyzer(samplerate=16000)
    assert sa.dominant_frequency(np.array([])) == 0.0
    assert np.all(sa.bands(np.array([])) == 0)
