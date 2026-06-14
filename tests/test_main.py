"""Tests for entry-point helpers in snoper.__main__ (no GUI, no real audio)."""

import snoper.__main__ as m
from snoper.config import Settings


def test_selftest_ok():
    # Imports + wires all modules; returns 0 on success.
    assert m._selftest() == 0


def test_main_selftest_arg(tmp_path, monkeypatch):
    import tempfile

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    assert m.main(["--selftest"]) == 0
    assert (tmp_path / "snoper_selftest.log").read_text().startswith("SELFTEST_OK")


def test_build_transcribe_callback_disabled():
    s = Settings(transcribe=False)
    assert m._build_transcribe_callback(s) is None


def test_build_transcribe_callback_enabled(tmp_path):
    s = Settings(recordings_dir=str(tmp_path), transcribe=True)
    cb = m._build_transcribe_callback(s)
    assert callable(cb)  # returns the queue's enqueue


def test_maybe_auto_update_disabled_is_noop():
    s = Settings(auto_update=False)
    # Should return immediately without spawning a thread or raising.
    assert m._maybe_auto_update(s) is None


def test_maybe_auto_update_runs_worker(monkeypatch):
    called = {}

    def fake_check_and_update(settings, on_status=None):
        called["ran"] = True
        return False

    import snoper.updater as up

    monkeypatch.setattr(up, "check_and_update", fake_check_and_update)

    s = Settings(auto_update=True, update_check_on_start=True, update_check_interval_h=0)
    m._maybe_auto_update(s)

    # worker runs on a daemon thread; give it a moment
    import time

    for _ in range(50):
        if called.get("ran"):
            break
        time.sleep(0.02)
    assert called.get("ran") is True


def test_run_headless_reports_capture_error(monkeypatch, tmp_path):
    # No real audio device -> recorder sets last_error; run_headless returns 1.
    import snoper.recorder as rec_mod

    class FailCapture:
        def __init__(self, settings):
            from snoper.audio.capture import CaptureError

            raise CaptureError("no device")

    monkeypatch.setattr(rec_mod, "AudioCapture", FailCapture)
    monkeypatch.setattr(rec_mod, "estimate_ambient_rms", lambda *a, **k: 0.0)

    s = Settings(recordings_dir=str(tmp_path), auto_calibrate=False)
    rc = m.run_headless(s)
    assert rc == 1
