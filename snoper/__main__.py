"""Snoper entry point.

Wires settings -> recorder -> tray. The recorder runs the capture/VOX/writer
pipeline on a background thread while the tray icon (always visible) reflects
state. Transcription, if enabled, runs in its own background worker.

Run with:  python -m snoper            (tray app)
           python -m snoper --headless (no tray, for servers/testing)
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import threading
import time

from .config import Settings
from .logging_setup import setup_logging
from .recorder import Recorder, RecorderState

log = logging.getLogger("snoper.main")


def _maybe_auto_update(settings: Settings) -> None:
    """Silent auto-update: one check at startup, then periodic re-checks.

    Runs on a daemon thread so it never blocks recording. The first check fires
    shortly after launch; if `update_check_interval_h > 0` it then re-checks on
    that interval, so a long-running install updates without needing a restart.
    If an update is found it installs silently and relaunches Snoper.
    """
    if not settings.auto_update:
        return

    interval_s = max(0.0, settings.update_check_interval_h) * 3600

    def run_once():
        try:
            from .updater import check_and_update

            return check_and_update(settings, on_status=lambda m: log.info("update: %s", m))
        except Exception:  # pragma: no cover - defensive
            log.exception("auto-update error")
            return False

    def worker():
        if settings.update_check_on_start:
            if run_once():
                return  # updating/exiting; installer takes over
        if interval_s <= 0:
            return
        while True:
            time.sleep(interval_s)
            if run_once():
                return

    threading.Thread(target=worker, name="snoper-update", daemon=True).start()


def _build_transcribe_callback(settings: Settings):
    if not settings.transcribe:
        return None
    try:
        from .transcribe.engine import TranscriptionQueue
    except Exception:  # pragma: no cover
        log.exception("transcription unavailable")
        return None
    tq = TranscriptionQueue(settings)
    tq.start()
    return tq.enqueue


def run_headless(settings: Settings) -> int:
    """Run without a tray (Ctrl-C to stop). Useful on servers and for testing."""
    rec = Recorder(
        settings,
        on_state=lambda s: log.info("state: %s", s.value),
        on_segment_complete=_build_transcribe_callback(settings),
    )
    rec.start()

    stop = {"v": False}

    def _sig(*_):
        stop["v"] = True

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)
    log.info("running headless; press Ctrl-C to stop")
    while not stop["v"] and rec.state is not RecorderState.STOPPED:
        time.sleep(0.2)
    rec.stop()
    if rec.last_error:
        log.error("recorder error: %s", rec.last_error)
        return 1
    return 0


def run_tray(settings: Settings) -> int:
    from .tray.icon import TrayApp

    open_settings = None
    try:
        from .ui.settings import open_settings_window

        open_settings = lambda: open_settings_window(settings)  # noqa: E731
    except Exception:
        open_settings = None

    open_browser = None
    try:
        from .ui.browser import open_browser_window

        open_browser = lambda: open_browser_window(settings)  # noqa: E731
    except Exception:
        open_browser = None

    tray_ref: dict = {}

    def on_state(s: RecorderState):
        app = tray_ref.get("app")
        if app:
            app.update_state(s)

    rec = Recorder(
        settings,
        on_state=on_state,
        on_segment_complete=_build_transcribe_callback(settings),
    )
    def check_updates():
        from .updater import check_and_update

        def notify(msg):
            print(f"[snoper:update] {msg}")
            a = tray_ref.get("app")
            if a and a._icon is not None:
                a._icon.notify(msg, "Snoper update")

        check_and_update(settings, on_status=notify)

    app = TrayApp(
        rec, settings,
        open_settings=open_settings,
        open_browser=open_browser,
        check_updates=check_updates,
    )
    tray_ref["app"] = app
    rec.start()
    app.run()  # blocks until Quit
    rec.stop()
    return 0


def _selftest() -> int:
    """Import-and-wire smoke test for the frozen exe.

    Exercises every module the app loads (including the lazily-imported tray, UI,
    transcription, updater and platform layers) and builds the core objects, then
    exits. Run as `Snoper.exe --selftest` on a real Windows runner in CI so a
    packaging/import regression fails the build instead of reaching users.
    """
    import importlib

    mods = [
        "snoper.config", "snoper.recorder", "snoper.updater", "snoper.version",
        "snoper.scheduler", "snoper.postprocess",
        "snoper.logging_setup", "snoper.single_instance", "snoper.secrets_store",
        "snoper.audio.vox", "snoper.audio.capture", "snoper.audio.writer",
        "snoper.audio.dsp", "snoper.audio.analyzer",
        "snoper.storage.index", "snoper.transcribe.engine",
        "snoper.tray.icon", "snoper.ui.settings", "snoper.ui.browser",
        "snoper.platform.autostart_win",
    ]
    for m in mods:
        importlib.import_module(m)
    # Build the core objects to catch wiring errors, not just import errors.
    from .config import Settings
    from .recorder import Recorder

    Recorder(Settings())
    print("SELFTEST_OK")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="snoper", description="Voice-activated recorder")
    parser.add_argument("--headless", action="store_true", help="run without tray icon")
    parser.add_argument("--selftest", action="store_true", help="import/wire smoke test, then exit")
    args = parser.parse_args(argv)

    if args.selftest:
        # Windowed exe has no console, so also write the result to a log file the
        # CI smoke-test can read to see exactly which module/import failed.
        import tempfile
        import traceback

        log_path = os.path.join(tempfile.gettempdir(), "snoper_selftest.log")
        try:
            rc = _selftest()
            with open(log_path, "w") as f:
                f.write("SELFTEST_OK\n")
            return rc
        except Exception as e:
            with open(log_path, "w") as f:
                f.write(f"SELFTEST_FAILED: {type(e).__name__}: {e}\n\n")
                f.write(traceback.format_exc())
            print(f"SELFTEST_FAILED: {type(e).__name__}: {e}")
            return 1

    setup_logging()
    log.info("Snoper starting (headless=%s)", args.headless)

    # Single-instance guard: never run two recorders against the same mic.
    from .single_instance import SingleInstance

    instance = SingleInstance("snoper")
    if not instance.acquire():
        log.warning("another Snoper instance is already running; exiting")
        return 0

    try:
        settings = Settings.load()
        from pathlib import Path

        if settings.recordings_dir:
            Path(settings.recordings_dir).mkdir(parents=True, exist_ok=True)

        _maybe_auto_update(settings)

        if args.headless:
            return run_headless(settings)
        try:
            return run_tray(settings)
        except RuntimeError:
            log.exception("tray unavailable; falling back to headless")
            return run_headless(settings)
    finally:
        instance.release()


if __name__ == "__main__":
    raise SystemExit(main())
