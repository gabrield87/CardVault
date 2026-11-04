# CardVault - semnează un fișier cu certificatul din Secrets (folosit în workflow)
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
#
# Necesită variabilele de mediu CODE_SIGN_PFX_BASE64 și CODE_SIGN_PASSWORD.
# Notă: certificatele OV/EV emise din 2023 au cheia pe token/HSM/cloud și nu mai
# vin ca fișier .pfx. Pentru ele, înlocuiește pașii de mai jos cu instrumentul
# furnizorului (ex. Azure Artifact Signing, DigiCert KeyLocker, SSL.com eSigner).

param([Parameter(Mandatory = $true)][string]$File)
$ErrorActionPreference = "Stop"

$pfx = Join-Path $env:RUNNER_TEMP "cv.pfx"
try {
    [IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($env:CODE_SIGN_PFX_BASE64))
    $signtool = Get-ChildItem "C:/Program Files (x86)/Windows Kits/10/bin/*/x64/signtool.exe" |
                Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $signtool) { throw "signtool.exe nu a fost găsit" }
    & $signtool.FullName sign /f $pfx /p $env:CODE_SIGN_PASSWORD `
        /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $File
    if ($LASTEXITCODE -ne 0) { throw "Semnarea a eșuat pentru $File" }
}
finally {
    Remove-Item $pfx -Force -ErrorAction SilentlyContinue
}
