# PyInstaller spec for Snoper (build on Windows).
#   pyinstaller build/snoper.spec
# Produces dist/Snoper.exe — a single windowed (no-console) tray app.

# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['../snoper/__main__.py'],
    pathex=[os.path.abspath('..')],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pystray._win32',
        'PIL._tkinter_finder',
        'sounddevice',
        '_sounddevice_data',
    ],
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
