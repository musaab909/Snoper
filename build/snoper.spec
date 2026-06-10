# PyInstaller spec for Snoper (build on Windows).
#   pyinstaller build/snoper.spec
# Produces dist/Snoper.exe — a single windowed (no-console) tray app.

# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Several snoper submodules are imported lazily (ui.*, transcribe.*, platform.*),
# so collect them all explicitly rather than relying on static analysis.
hidden = [
    'pystray._win32',
    'PIL._tkinter_finder',
    'sounddevice',
    '_sounddevice_data',
] + collect_submodules('snoper')

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
