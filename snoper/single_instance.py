"""Single-instance guard.

Prevents two Snoper processes from recording the same microphone simultaneously.
Uses a lock file with an exclusive OS-level lock (msvcrt on Windows, fcntl on
POSIX) so a crashed process's lock is released automatically by the OS.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

log = logging.getLogger("snoper.single_instance")


class SingleInstance:
    def __init__(self, name: str = "snoper"):
        self._path = Path(tempfile.gettempdir()) / f"{name}.lock"
        self._fh: object | None = None

    def acquire(self) -> bool:
        """Return True if this is the only instance; False if one already holds it."""
        try:
            self._fh = open(self._path, "a+")
        except OSError:
            log.exception("could not open lock file %s", self._path)
            return True  # fail open: don't block the app on lock-file issues

        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            # Lock held by another process.
            self._fh.close()
            self._fh = None
            return False

        self._fh.seek(0)
        self._fh.truncate()
        self._fh.write(str(os.getpid()))
        self._fh.flush()
        return True

    def release(self) -> None:
        if self._fh is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            self._fh.close()
            self._fh = None
