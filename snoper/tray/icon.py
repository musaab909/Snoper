"""System-tray icon with a visible recording-state indicator.

By design Snoper is NOT a stealth recorder: the tray icon is always shown and its
color reflects whether audio is actively being captured (grey = listening,
red = recording, amber = paused). This visible indicator is intentional and not
configurable off.
"""

from __future__ import annotations

import os
import subprocess
import sys

from ..recorder import Recorder, RecorderState

try:
    import pystray  # type: ignore
    from PIL import Image, ImageDraw  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pystray = None
    Image = ImageDraw = None


_COLORS = {
    RecorderState.STOPPED: (120, 120, 120),
    RecorderState.LISTENING: (90, 160, 90),
    RecorderState.RECORDING: (220, 50, 50),
    RecorderState.PAUSED: (230, 170, 40),
}


def _make_image(color):
    img = Image.new("RGB", (64, 64), (30, 30, 30))
    d = ImageDraw.Draw(img)
    d.ellipse((12, 12, 52, 52), fill=color)
    return img


class TrayApp:
    def __init__(self, recorder: Recorder, settings, open_settings=None, open_browser=None, check_updates=None):
        if pystray is None:
            raise RuntimeError(
                "pystray/Pillow not installed. Install with: pip install pystray pillow"
            )
        self.recorder = recorder
        self.settings = settings
        self.open_settings = open_settings
        self.open_browser = open_browser
        self.check_updates = check_updates
        self._icon: pystray.Icon | None = None

    def _label(self) -> str:
        return f"Snoper — {self.recorder.state.value}"

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem(
                lambda _: ("Resume" if self.recorder.paused else "Pause"),
                self._toggle_pause,
            ),
            pystray.MenuItem("Open recordings folder", self._open_folder),
            pystray.MenuItem("Recordings & search…", self._open_browser) if self.open_browser else None,
            pystray.MenuItem("Settings…", self._open_settings) if self.open_settings else None,
            pystray.MenuItem("Check for updates…", self._check_updates) if self.check_updates else None,
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )

    def update_state(self, state: RecorderState) -> None:
        if self._icon is not None:
            self._icon.icon = _make_image(_COLORS.get(state, (120, 120, 120)))
            self._icon.title = self._label()

    # --- menu actions ---
    def _toggle_pause(self, *_):
        if self.recorder.paused:
            self.recorder.resume()
        else:
            self.recorder.pause()
        self.update_state(self.recorder.state)

    def _open_folder(self, *_):
        path = self.settings.recordings_dir
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _open_settings(self, *_):
        if self.open_settings:
            self.open_settings()

    def _open_browser(self, *_):
        if self.open_browser:
            self.open_browser()

    def _check_updates(self, *_):
        if self.check_updates:
            import threading

            threading.Thread(target=self.check_updates, daemon=True).start()
            if self._icon is not None:
                self._icon.notify("Checking for updates…", "Snoper")

    def _quit(self, *_):
        self.recorder.stop()
        if self._icon is not None:
            self._icon.stop()

    def run(self) -> None:
        self._icon = pystray.Icon(
            "snoper",
            icon=_make_image(_COLORS[RecorderState.STOPPED]),
            title=self._label(),
            menu=self._build_menu(),
        )
        self._icon.run()
