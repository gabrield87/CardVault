@echo off
REM CardVault - build local (Windows x64). Rezultat: dist\CardVault\
REM Copyright (c) 2026 Gabriel Dobre. All rights reserved.
REM Necesita Python 3.12 doar pe calculatorul pe care faci build-ul.
REM Versiunea oficiala vine din GitHub Release; local se foloseste cardvault\_version.py.
cd /d "%~dp0"
if not exist .venv ( python -m venv .venv || goto :err )
call .venv\Scripts\activate.bat
powershell -NoProfile -ExecutionPolicy Bypass -File tools\build_windows.ps1 || goto :err
echo.
echo  Gata! Aplicatia este in: dist\CardVault\CardVault.exe
pause
exit /b 0
:err
echo Build esuat.
pause
exit /b 1
