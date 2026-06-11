"""Tests for the single-instance guard."""

from snoper.single_instance import SingleInstance


def test_second_instance_is_blocked(tmp_path, monkeypatch):
    # isolate the lock file to the tmp dir
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

    a = SingleInstance("snoper-test")
    b = SingleInstance("snoper-test")
    try:
        assert a.acquire() is True
        assert b.acquire() is False  # second one blocked while first holds it
    finally:
        a.release()


def test_lock_released_allows_reacquire(tmp_path, monkeypatch):
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

    a = SingleInstance("snoper-test")
    assert a.acquire() is True
    a.release()

    b = SingleInstance("snoper-test")
    try:
        assert b.acquire() is True  # reacquire after release
    finally:
        b.release()
