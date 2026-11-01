@echo off
setlocal
cd /d "%~dp0"
title Build Stellar Spectrum EXE

set "PY="
if exist "D:\python\python.exe" set "PY=D:\python\python.exe"
if not defined PY (
    where py >nul 2>nul && set "PY=py"
)
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo Python not found.
    pause
    exit /b 1
)

"%PY%" -m pip install --disable-pip-version-check pyinstaller
if errorlevel 1 (
    pause
    exit /b 1
)

"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed --name StellarSpectrum --collect-submodules soundcard main.py
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Build complete: dist\StellarSpectrum\StellarSpectrum.exe
echo You can copy that folder anywhere and run the exe.
pause
