# CardVault - signs a file with the certificate stored in GitHub Secrets (used by the workflow)
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
#
# Requires the CODE_SIGN_PFX_BASE64 and CODE_SIGN_PASSWORD environment variables.
# Note: OV/EV certificates issued since 2023 keep the key on a token/HSM/cloud
# service and no longer come as a .pfx file. For those, replace the steps below
# with the provider's tool (e.g. Azure Artifact Signing, DigiCert KeyLocker,
# SSL.com eSigner).

param([Parameter(Mandatory = $true)][string]$File)
$ErrorActionPreference = "Stop"

$pfx = Join-Path $env:RUNNER_TEMP "cv.pfx"
try {
    [IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($env:CODE_SIGN_PFX_BASE64))
    $signtool = Get-ChildItem "C:/Program Files (x86)/Windows Kits/10/bin/*/x64/signtool.exe" |
                Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $signtool) { throw "signtool.exe not found" }
    & $signtool.FullName sign /f $pfx /p $env:CODE_SIGN_PASSWORD `
        /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $File
    if ($LASTEXITCODE -ne 0) { throw "Signing failed for $File" }
}
finally {
    Remove-Item $pfx -Force -ErrorAction SilentlyContinue
}
