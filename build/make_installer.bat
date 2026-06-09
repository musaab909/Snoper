@echo off
REM ============================================================
REM  Compile the Snoper installer with Inno Setup.
REM  Requires Inno Setup 6 installed (ISCC.exe on PATH or in the
REM  default location). Run build_windows.bat first.
REM  Produces: build\Output\Snoper-Setup.exe
REM ============================================================
setlocal

cd /d "%~dp0"

if not exist "..\dist\Snoper.exe" (
    echo dist\Snoper.exe not found. Run build_windows.bat first.
    exit /b 1
)

set ISCC=ISCC.exe
where %ISCC% >nul 2>nul
if errorlevel 1 (
    set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
)

if not exist "%ISCC%" (
    echo Inno Setup compiler ISCC.exe not found.
    echo Install Inno Setup 6 from https://jrsoftware.org/isdl.php
    exit /b 1
)

"%ISCC%" installer.iss
echo.
echo Done. Installer: build\Output\Snoper-Setup.exe
endlocal
