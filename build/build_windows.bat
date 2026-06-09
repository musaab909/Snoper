@echo off
REM ============================================================
REM  Snoper - Windows build script
REM  Run this on a Windows PC (not macOS/Linux).
REM  Produces: dist\Snoper.exe  (standalone tray app)
REM ============================================================
setlocal

cd /d "%~dp0\.."

echo [1/4] Checking Python...
python --version || (echo Python not found on PATH & exit /b 1)

echo [2/4] Creating venv and installing dependencies...
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
REM Optional heavy extras (uncomment if you want them bundled):
REM python -m pip install faster-whisper cryptography

echo [3/4] Running tests...
python -m pytest -q || (echo Tests failed & exit /b 1)

echo [4/4] Building Snoper.exe with PyInstaller...
pyinstaller --noconfirm --clean build\snoper.spec

echo.
echo Done. Output: dist\Snoper.exe
echo To build the installer, run: build\make_installer.bat
endlocal
