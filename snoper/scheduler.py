"""Recording schedule: only allow capture during configured time windows.

A schedule is a list of windows, each with weekdays + start/end clock times.
`is_active(now)` tells the recorder whether capture is currently allowed. With no
windows configured, recording is always allowed (24/7).

Times are local "HH:MM"; windows may cross midnight (e.g. 22:00–02:00).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time


def _parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


@dataclass
class Window:
    start: str            # "HH:MM"
    end: str              # "HH:MM"
    days: list[int]       # 0=Mon .. 6=Sun; empty = every day

    def contains(self, now: datetime) -> bool:
        start = _parse_hhmm(self.start)
        end = _parse_hhmm(self.end)
        t = now.time()
        wd = now.weekday()

        if self.days and wd not in self.days:
            # crossing-midnight windows can belong to the previous day
            if not (start > end and (wd - 1) % 7 in self.days):
                return False

        if start <= end:
            return start <= t <= end
        # crosses midnight: active if after start OR before end
        return t >= start or t <= end


class Schedule:
    def __init__(self, windows: list[Window] | None = None):
        self.windows = windows or []

    @classmethod
    def from_config(cls, raw: list | None) -> Schedule:
        if not raw:
            return cls([])
        return cls([Window(w["start"], w["end"], w.get("days", [])) for w in raw])

    def is_active(self, now: datetime | None = None) -> bool:
        if not self.windows:
            return True  # no schedule = always on
        now = now or datetime.now()
        return any(w.contains(now) for w in self.windows)
