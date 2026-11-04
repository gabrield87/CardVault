# CardVault - build Windows x64 (folosit de ambele workflow-uri și local)
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
#
#   pwsh tools/build_windows.ps1 -Version 1.3.0
#   (fără -Version: se folosește versiunea din cardvault/_version.py)
#
# Rezultat: dist/CardVault/ (CardVault.exe + _internal/ + banks/ + LICENSE.txt)

param(
    [string]$Version = ""
)
$ErrorActionPreference = "Stop"
# Python să folosească UTF-8 (consola serverelor de build e cp1252)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not $Version) {
    # build local: versiunea din cardvault/_version.py
    $m = Select-String -Path "cardvault/_version.py" -Pattern '__version__\s*=\s*"([^"]+)"'
    $Version = $m.Matches[0].Groups[1].Value
}

function Run($exe, [string[]]$argList) {
    & $exe @argList
    if ($LASTEXITCODE -ne 0) { throw "$exe a eșuat (cod $LASTEXITCODE)" }
}

Run python @("-m", "pip", "install", "--upgrade", "pip")
Run python @("-m", "pip", "install", "-r", "requirements.txt", "pyinstaller")
Run python @("tools/set_version.py", $Version)

# Module de rețea care NU sunt folosite: le scoatem complet din pachet,
# ca aplicația să nu conțină deloc cod de TLS/e-mail/FTP/servere.
$noNet = @("ssl", "_ssl", "ftplib", "smtplib", "imaplib", "poplib", "nntplib",
           "telnetlib", "xmlrpc", "http.server", "socketserver", "webbrowser",
           "PySide6.QtNetwork", "PySide6.QtWebEngineCore", "PySide6.QtWebSockets")
$excludes = @("tkinter", "PySide6.QtQml", "PySide6.QtQuick") + $noNet |
            ForEach-Object { "--exclude-module=$_" }

$pyiArgs = @("-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
             "--name", "CardVault",
             "--icon", "assets/icon.ico",
             "--version-file", "version_info.txt",
             "--add-data", "assets;assets") + $excludes + @("main.py")
Run python $pyiArgs

$app = "dist/CardVault"
$qt = "$app/_internal/PySide6"
Remove-Item "$qt/opengl32sw.dll" -ErrorAction SilentlyContinue
# păstrăm doar traducerile Qt pentru limbile aplicației
Get-ChildItem "$qt/translations" -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notmatch '^qtbase_(en|de|fr|es|it)\.qm$' } |
    Remove-Item -Force -Recurse

New-Item -ItemType Directory -Force "$app/banks" | Out-Null
Copy-Item "banks/*" "$app/banks/" -Force
Copy-Item "LICENSE" "$app/LICENSE.txt" -Force
Write-Host "Build gata: $app (versiunea $Version)"
