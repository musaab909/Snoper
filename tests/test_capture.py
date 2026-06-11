"""Synthetic-audio tests for AudioCapture.

Exercises the real capture code paths — stereo->mono mixing in the stream
callback and the re-framing buffer in frames() — by injecting synthetic audio
instead of using a microphone. Runs in CI on the real Windows runner (which has
sounddevice installed but no mic), so the audio plumbing is covered without
hardware. Skipped where sounddevice isn't installed (e.g. dev macOS).
"""

import threading

import numpy as np
import pytest

sd = pytest.importorskip("sounddevice")  # noqa: F841  (skip if not installed)

from snoper.audio.capture import AudioCapture
from snoper.config import Settings


def _settings():
    return Settings(samplerate=16000, channels=1, frame_ms=30)  # frame_samples = 480


def test_callback_mixes_stereo_to_mono():
    cap = AudioCapture(_settings())
    # stereo block: left=0.2, right=0.4 -> mono mean = 0.3
    stereo = np.column_stack([
        np.full(480, 0.2, dtype=np.float32),
        np.full(480, 0.4, dtype=np.float32),
    ])
    cap._callback(stereo, 480, None, None)
    mono = cap._q.get_nowait()
    assert mono.ndim == 1
    assert mono.shape == (480,)
    assert np.allclose(mono, 0.3, atol=1e-6)


def test_frames_reassembles_exact_frame_sizes():
    """Odd-sized input chunks must be re-chunked into exact frame_samples frames."""
    cap = AudioCapture(_settings())
    n = cap._frame_samples  # 480
    stop = threading.Event()

    # Feed 1000 samples as two uneven chunks (300 + 700) -> expect two full 480 frames.
    ramp = np.arange(1000, dtype=np.float32)
    cap._q.put(ramp[:300])
    cap._q.put(ramp[300:])

    out = []

    def consume():
        for f in cap.frames(stop):
            out.append(f)
            if len(out) >= 2:
                stop.set()

    t = threading.Thread(target=consume, daemon=True)
    t.start()
    t.join(timeout=3)

    assert len(out) == 2
    assert all(f.shape == (n,) for f in out)
    # content is preserved in order across the re-chunking
    assert np.array_equal(np.concatenate(out), ramp[: 2 * n])


def test_frames_stops_on_event():
    cap = AudioCapture(_settings())
    stop = threading.Event()
    stop.set()  # already stopped
    # generator should exit immediately without yielding
    assert list(cap.frames(stop)) == []
