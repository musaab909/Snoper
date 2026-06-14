"""Tests for Recorder control API and capture fallbacks (no hardware)."""

import snoper.audio.capture as cap
from snoper.config import MODE_CONTINUOUS, MODE_VOX, Settings
from snoper.recorder import Recorder, RecorderState


def test_recorder_pause_resume_state():
    r = Recorder(Settings())
    assert r.state is RecorderState.STOPPED
    r.pause()
    assert r.paused is True
    assert r.state is RecorderState.PAUSED
    r.resume()
    assert r.paused is False
    assert r.state is RecorderState.LISTENING


def test_recorder_build_engine_continuous(monkeypatch):
    import snoper.recorder as rec_mod

    monkeypatch.setattr(rec_mod, "estimate_ambient_rms", lambda *a, **k: 0.0)
    s = Settings(mode=MODE_CONTINUOUS, auto_calibrate=False)
    eng = Recorder(s)._build_engine()
    # continuous mode treats every frame as loud (threshold 0)
    assert eng.threshold == 0.0


def test_recorder_build_engine_vox_calibrates(monkeypatch):
    import snoper.recorder as rec_mod

    monkeypatch.setattr(rec_mod, "estimate_ambient_rms", lambda *a, **k: 0.1)
    s = Settings(mode=MODE_VOX, auto_calibrate=True, vox_threshold=0.02, calibration_margin=3.0)
    eng = Recorder(s)._build_engine()
    # threshold raised to ambient * margin = 0.3
    assert eng.threshold >= 0.3 - 1e-9


def test_list_input_devices_empty_without_sd(monkeypatch):
    monkeypatch.setattr(cap, "_sd", None)
    assert cap.list_input_devices() == []


def test_estimate_ambient_rms_zero_without_sd(monkeypatch):
    monkeypatch.setattr(cap, "_sd", None)
    assert cap.estimate_ambient_rms(Settings()) == 0.0


def test_capture_init_raises_without_sd(monkeypatch):
    monkeypatch.setattr(cap, "_sd", None)
    import pytest

    with pytest.raises(cap.CaptureError):
        cap.AudioCapture(Settings())
