# Snoper — Voice-Activated Audio Recorder

A transparent, voice-activated (VOX) audio recorder for Windows. It automatically
starts recording when it detects sound, stops during silence, transcribes with
Whisper, and keeps a searchable archive — efficient hands-free capture for
dictation and meetings.

> **Transparent by design.** Snoper always shows a visible system-tray indicator
> while it runs (grey = listening, red = recording, amber = paused). It does **not**
> include a hidden/stealth mode. Only record people who know they're being recorded —
> covert recording is illegal in many places.

## Features

- **Voice-activated (VOX)** start/stop with adjustable threshold + auto-calibration
- **Modes:** VOX, dictation (single file + timestamp index), continuous
- **Pre-roll** buffer so the first syllable isn't clipped; silence hysteresis keeps
  natural pauses inside one segment
- **Mic + system-audio** capture (WASAPI loopback on Windows)
- **Whisper transcription** (faster-whisper) with searchable SQLite/FTS index
- **Auto-start on Windows login** (per-user, no admin)
- **Tray UI** with pause/resume, open-folder, settings, quit

## Install

```bash
pip install -r requirements.txt
```

`faster-whisper` is optional (only needed for transcription).

## Run

```bash
python -m snoper            # tray app (recommended)
python -m snoper --headless # no tray; Ctrl-C to stop (servers/testing)
```

Recordings + transcripts land in `~/Snoper/Recordings` (configurable). Settings
persist to `%APPDATA%/Snoper/config.json` (Windows) or `~/.config/Snoper/config.json`.

## Build a Windows .exe

On a Windows machine:

```bash
pip install -r requirements.txt
pyinstaller build/snoper.spec
# -> dist/Snoper.exe  (windowed tray app)
```

## Architecture

```
snoper/
  __main__.py        entry point (tray / headless)
  config.py          settings (JSON persistence)
  recorder.py        capture -> VOX -> writer controller (background thread)
  audio/
    capture.py       device enumeration + frame-yielding input stream
    vox.py           VOX state machine (pure, unit-tested)
    writer.py        timestamped WAV segments / dictation file
  tray/icon.py       visible tray indicator + menu
  transcribe/engine.py   background Whisper worker
  storage/index.py   SQLite + FTS search index
  platform/autostart_win.py   Windows boot registration
  ui/settings.py     Tkinter settings window
```

## Tests

```bash
pytest -q
```

Covers the VOX state machine, segment writer (real WAV files), the search index,
and the full recorder pipeline (with a fake audio source — no hardware required).

## Platform notes

Core logic is cross-platform and is developed/tested on macOS. Windows-specific
features — boot startup, WASAPI system-audio loopback, and the packaged `.exe` —
must be run and verified on Windows.
```
