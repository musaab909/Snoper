# PyInstaller spec for Snoper (build on Windows).
#   pyinstaller build/snoper.spec
# Produces dist/Snoper.exe — a single windowed (no-console) tray app.

# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# Ensure the repo root is importable so collect_submodules can actually find the
# `snoper` package while this spec runs (the spec body executes before PyInstaller
# injects pathex into sys.path). Without this, lazily-imported submodules such as
# snoper.audio.analyzer are silently omitted from the bundle.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(SPECPATH), '.'))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

_snoper_submodules = collect_submodules('snoper')
assert any(m == 'snoper.audio.analyzer' for m in _snoper_submodules), (
    "collect_submodules('snoper') failed to enumerate the package; "
    f"got {_snoper_submodules!r}"
)

# Several snoper submodules are imported lazily (ui.*, transcribe.*, platform.*),
# so collect them all rather than relying on static analysis.
hidden = [
    'pystray._win32',
    'PIL._tkinter_finder',
    'sounddevice',
    '_sounddevice_data',
] + _snoper_submodules

a = Analysis(
    # Entry is the launcher (NOT snoper/__main__.py) so the package imports as a
    # proper package and relative imports resolve in the frozen exe.
    ['../launcher.py'],
    pathex=[os.path.abspath('..')],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='Snoper',
    debug=False,
    strip=False,
    upx=True,
    console=False,   # windowed: launches straight to the tray, no console window
)
