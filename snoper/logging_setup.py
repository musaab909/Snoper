"""Centralized logging for Snoper.

The shipped app is a *windowed* exe with no console, so stdout/stderr go nowhere.
This module routes everything to a rotating log file (and to the console in dev),
and installs a global exception hook so otherwise-invisible crashes are recorded.

Call ``setup_logging()`` once at startup, then use ``logging.getLogger(__name__)``
throughout. Never use ``print()`` for diagnostics.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import threading
from pathlib import Path

_CONFIGURED = False


def log_dir() -> Path:
    """Per-user log directory (platform-appropriate)."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    d = base / "Snoper" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_file() -> Path:
    return log_dir() / "snoper.log"


def setup_logging(level: int = logging.INFO) -> Path:
    """Configure root logging once. Returns the active log file path."""
    global _CONFIGURED
    path = log_file()
    if _CONFIGURED:
        return path

    root = logging.getLogger()
    root.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s [%(threadName)s] %(message)s"
    )

    # Rotating file: 1 MB x 5 backups keeps logs bounded.
    fh = logging.handlers.RotatingFileHandler(
        path, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Console handler only when a console exists (dev runs), not in the frozen exe.
    if not getattr(sys, "frozen", False):
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        root.addHandler(ch)

    _install_excepthooks()
    _CONFIGURED = True
    logging.getLogger("snoper").info("logging initialized -> %s", path)
    return path


def _install_excepthooks() -> None:
    """Capture uncaught exceptions on the main thread and worker threads."""
    log = logging.getLogger("snoper.crash")

    def handle(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        log.critical("uncaught exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = handle

    # Python 3.8+: capture exceptions raised in threads too.
    def thread_hook(args):
        if issubclass(args.exc_type, KeyboardInterrupt):
            return
        log.critical(
            "uncaught exception in thread %s",
            args.thread.name if args.thread else "?",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = thread_hook
