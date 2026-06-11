"""Integration test: Recorder pipeline end-to-end with a fake audio source.

Avoids real hardware by monkeypatching AudioCapture with a generator that emits
synthetic loud/quiet frames, then asserts files land on disk and state callbacks
fire START/STOP transitions.
"""

import time

import numpy as np

import snoper.recorder as recorder_mod
from snoper.config import MODE_VOX, Settings
from snoper.recorder import Recorder, RecorderState

SAMPLES = 480


def loud():
    return np.full(SAMPLES, 0.5, dtype=np.float32)


def quiet():
    return np.zeros(SAMPLES, dtype=np.float32)


class FakeCapture:
    """Stand-in for AudioCapture: replays a fixed frame script then idles."""

    def __init__(self, settings):
        self.settings = settings
        # speech burst, then enough silence to trigger STOP, then trailing quiet
        self.script = [loud()] * 10 + [quiet()] * 10 + [loud()] * 5 + [quiet()] * 10

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def frames(self, stop_event):
        for f in self.script:
            if stop_event.is_set():
                return
            yield f
        # keep stream "open" idling until stopped
        while not stop_event.is_set():
            time.sleep(0.01)
            yield quiet()


def test_recorder_pipeline_writes_files(tmp_path, monkeypatch):
    monkeypatch.setattr(recorder_mod, "AudioCapture", FakeCapture)
    # skip mic-based calibration
    monkeypatch.setattr(recorder_mod, "estimate_ambient_rms", lambda *a, **k: 0.0)

    settings = Settings(
        recordings_dir=str(tmp_path),
        samplerate=16000,
        frame_ms=30,
        mode=MODE_VOX,
        vox_threshold=0.02,
        auto_calibrate=False,
        start_frames=2,
        silence_timeout_s=0.09,  # ~3 quiet frames
        min_segment_s=0.0,
    )

    states = []
    rec = Recorder(settings, on_state=states.append)
    rec.start()

    # wait for at least one full START->STOP cycle
    deadline = time.time() + 5
    while time.time() < deadline:
        if RecorderState.RECORDING in states and states.count(RecorderState.LISTENING) >= 2:
            break
        time.sleep(0.05)
    rec.stop()

    wavs = list(tmp_path.glob("*.wav"))
    assert len(wavs) >= 1, f"expected recordings, states={states}"
    assert RecorderState.RECORDING in states
    assert rec.last_error is None
