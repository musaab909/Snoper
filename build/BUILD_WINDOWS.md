# Building the Snoper Windows installer

The `.exe` and installer **must be built on Windows** — PyInstaller and Inno Setup
produce native Windows binaries and cannot cross-compile from macOS/Linux. Use a
real Windows PC or a Windows 10/11 VM.

## Prerequisites (on the Windows machine)

1. **Python 3.10+** — https://www.python.org/downloads/windows/
   (check "Add Python to PATH" during install)
2. **Inno Setup 6** (for the installer) — https://jrsoftware.org/isdl.php
3. Copy this whole project folder to the Windows machine.

## One-time / quick build

Open **Command Prompt** in the project folder and run:

```bat
build\build_windows.bat
```

This creates a venv, installs deps, runs the tests, and produces:

```
dist\Snoper.exe        <- standalone tray app (double-click to run)
```

Then build the installer:

```bat
build\make_installer.bat
```

Which produces:

```
build\Output\Snoper-Setup.exe   <- the installer you distribute/run
```

## Installing

Run **`Snoper-Setup.exe`**. The wizard offers two optional checkboxes:

- **Create a desktop shortcut**
- **Start Snoper automatically when Windows starts** (adds a per-user Run entry;
  no admin required)

After install, Snoper launches to the **system tray** with a visible status dot
(grey = listening, red = recording, amber = paused). Right-click the tray icon for
Pause/Resume, Recordings & search, Settings, and Quit.

## Optional features that need extra packages

Re-run the build after installing these into the venv to bundle them:

```bat
call .venv\Scripts\activate.bat
pip install faster-whisper      REM transcription
pip install cryptography        REM recording encryption
```

For **MP3 output**, install `ffmpeg` and ensure `ffmpeg.exe` is on PATH on the
machine that runs Snoper (it's invoked at runtime, not bundled).

## Notes

- The exe is built **windowed** (`console=False`), so it launches straight to the
  tray with no console window — but it is **not** hidden: the tray icon is always
  shown by design. There is no stealth mode.
- First launch creates `%APPDATA%\Snoper\config.json` and a recordings folder at
  `%USERPROFILE%\Snoper\Recordings`.
