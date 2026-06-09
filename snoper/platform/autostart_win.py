"""Windows auto-start on login via the per-user Run registry key.

Per-user (HKCU) means no admin rights required. The app launches to the tray on
login. Enable/disable is toggled from the settings UI. No-ops on non-Windows so
the module is importable during macOS development.
"""

from __future__ import annotations

import os
import sys

APP_NAME = "Snoper"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _is_windows() -> bool:
    return os.name == "nt"


def _launch_command() -> str:
    """Command Windows runs at login.

    For a frozen PyInstaller .exe this is just the exe path; from source it's
    `pythonw -m snoper` so no console window appears.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    runner = pyw if os.path.exists(pyw) else sys.executable
    return f'"{runner}" -m snoper'


def is_enabled() -> bool:
    if not _is_windows():
        return False
    import winreg  # type: ignore

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False


def enable() -> None:
    if not _is_windows():
        raise RuntimeError("autostart registration is only supported on Windows")
    import winreg  # type: ignore

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _launch_command())


def disable() -> None:
    if not _is_windows():
        return
    import winreg  # type: ignore

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass


def apply(enabled: bool) -> None:
    if enabled:
        enable()
    else:
        disable()
