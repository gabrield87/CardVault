# CardVault - Windows x64 build (used by both workflows and locally)
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
#
#   pwsh tools/build_windows.ps1 -Version 1.3.0
#   (without -Version: uses the version from cardvault/_version.py)
#
# Output: dist/CardVault/ (CardVault.exe + _internal/ + banks/ + LICENSE.txt)

param(
    [string]$Version = ""
)
$ErrorActionPreference = "Stop"
# Make Python use UTF-8 (Windows build servers default to a cp1252 console)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not $Version) {
    # local build: version from cardvault/_version.py
    $m = Select-String -Path "cardvault/_version.py" -Pattern '__version__\s*=\s*"([^"]+)"'
    $Version = $m.Matches[0].Groups[1].Value
}

function Run($exe, [string[]]$argList) {
    & $exe @argList
    if ($LASTEXITCODE -ne 0) { throw "$exe failed (exit code $LASTEXITCODE)" }
}

Run python @("-m", "pip", "install", "--upgrade", "pip")
Run python @("-m", "pip", "install", "-r", "requirements.txt", "pyinstaller")
Run python @("tools/set_version.py", $Version)

# Unused networking modules are removed from the package entirely,
# so the app contains no TLS / e-mail / FTP / server code at all.
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
# keep only the Qt translations for the app's languages
Get-ChildItem "$qt/translations" -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notmatch '^qtbase_(en|de|fr|es|it)\.qm$' } |
    Remove-Item -Force -Recurse

New-Item -ItemType Directory -Force "$app/banks" | Out-Null
Copy-Item "banks/*" "$app/banks/" -Force
Copy-Item "LICENSE" "$app/LICENSE.txt" -Force
Write-Host "Build complete: $app (version $Version)"
