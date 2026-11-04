@echo off
REM CardVault - run from source. Copyright (c) 2026 Gabriel Dobre.
cd /d "%~dp0"
if not exist .venv (
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)
start "" pythonw main.py
