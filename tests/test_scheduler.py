"""Tests for the recording schedule / time windows."""

from datetime import datetime

from snoper.scheduler import Schedule, Window


def dt(y=2026, mo=6, d=10, h=10, mi=0):  # 2026-06-10 is a Wednesday (weekday 2)
    return datetime(y, mo, d, h, mi)


def test_no_windows_always_active():
    assert Schedule([]).is_active(dt()) is True


def test_simple_window_inside_and_outside():
    s = Schedule([Window("09:00", "17:00", days=[])])
    assert s.is_active(dt(h=10)) is True
    assert s.is_active(dt(h=8)) is False
    assert s.is_active(dt(h=18)) is False


def test_window_restricted_to_weekdays():
    # only Monday (0)
    s = Schedule([Window("00:00", "23:59", days=[0])])
    assert s.is_active(dt(d=10)) is False           # Wednesday
    assert s.is_active(dt(d=8)) is True             # Monday 2026-06-08


def test_window_crossing_midnight():
    s = Schedule([Window("22:00", "02:00", days=[])])
    assert s.is_active(dt(h=23)) is True
    assert s.is_active(dt(h=1)) is True
    assert s.is_active(dt(h=12)) is False


def test_from_config_roundtrip():
    s = Schedule.from_config([{"start": "09:00", "end": "10:00", "days": [2]}])
    assert s.is_active(dt(h=9, mi=30)) is True
    assert s.is_active(dt(h=11)) is False
