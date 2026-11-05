@echo off
REM CardVault - local build (Windows x64). Output: dist\CardVault\
REM Copyright (c) 2026 Gabriel Dobre. All rights reserved.
REM Requires Python 3.12 only on the build machine. End users need nothing.
REM The official version comes from the GitHub Release; locally cardvault\_version.py is used.
cd /d "%~dp0"
if not exist .venv ( python -m venv .venv || goto :err )
call .venv\Scripts\activate.bat
powershell -NoProfile -ExecutionPolicy Bypass -File tools\build_windows.ps1 || goto :err
echo.
echo  Done! The application is in: dist\CardVault\CardVault.exe
pause
exit /b 0
:err
echo Build failed.
pause
exit /b 1
