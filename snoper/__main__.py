"""Snoper entry point.

Wires settings -> recorder -> tray. The recorder runs the capture/VOX/writer
pipeline on a background thread while the tray icon (always visible) reflects
state. Transcription, if enabled, runs in its own background worker.

Run with:  python -m snoper            (tray app)
           python -m snoper --headless (no tray, for servers/testing)
"""

from __future__ import annotations

import argparse
import signal
import sys
import time

import threading

from .config import Settings
from .recorder import Recorder, RecorderState


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

            return check_and_update(settings, on_status=lambda m: print(f"[snoper:update] {m}"))
        except Exception as e:  # pragma: no cover - defensive
            print(f"[snoper] auto-update error: {e}")
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
    except Exception as e:  # pragma: no cover
        print(f"[snoper] transcription unavailable: {e}", file=sys.stderr)
        return None
    tq = TranscriptionQueue(settings)
    tq.start()
    return tq.enqueue


def run_headless(settings: Settings) -> int:
    """Run without a tray (Ctrl-C to stop). Useful on servers and for testing."""
    rec = Recorder(
        settings,
        on_state=lambda s: print(f"[snoper] {s.value}"),
        on_segment_complete=_build_transcribe_callback(settings),
    )
    rec.start()

    stop = {"v": False}

    def _sig(*_):
        stop["v"] = True

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)
    print("[snoper] running headless; press Ctrl-C to stop")
    while not stop["v"] and rec.state is not RecorderState.STOPPED:
        time.sleep(0.2)
    rec.stop()
    if rec.last_error:
        print(f"[snoper] error: {rec.last_error}", file=sys.stderr)
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

    tray_ref = {}

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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="snoper", description="Voice-activated recorder")
    parser.add_argument("--headless", action="store_true", help="run without tray icon")
    args = parser.parse_args(argv)

    settings = Settings.load()
    settings.recordings_dir and __import__("pathlib").Path(settings.recordings_dir).mkdir(
        parents=True, exist_ok=True
    )

    _maybe_auto_update(settings)

    if args.headless:
        return run_headless(settings)
    try:
        return run_tray(settings)
    except RuntimeError as e:
        print(f"[snoper] {e}\nFalling back to headless mode.", file=sys.stderr)
        return run_headless(settings)


if __name__ == "__main__":
    raise SystemExit(main())
