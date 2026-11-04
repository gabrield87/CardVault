# CardVault - pregătește conținutul pachetului MSIX pentru Microsoft Store
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
#
#   python tools/make_msix.py --version 1.3.0 --identity <Name> \
#       --publisher "CN=...." --publisher-name "Gabriel Dobre" \
#       --src dist/CardVault --out build/msix
#
# Valorile --identity și --publisher le găsești în Partner Center:
#   App → Product management → Product identity
#     Package/Identity/Name        -> --identity
#     Package/Identity/Publisher   -> --publisher   (începe cu "CN=")
#     Package/Properties/PublisherDisplayName -> --publisher-name
#
# Apoi:  makeappx pack /d build/msix /p CardVault.msix /o
# Pachetul NU trebuie semnat de tine: Microsoft Store îl semnează la publicare.

import argparse
import os
import re
import shutil
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LANGS = ["en-us", "ro-ro", "de-de", "fr-fr", "es-es", "it-it"]

MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<!-- Generat de tools/make_msix.py. CardVault (c) Gabriel Dobre. -->
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap rescap">

  <Identity Name="{identity}" Publisher="{publisher}" Version="{version}" ProcessorArchitecture="x64" />

  <Properties>
    <DisplayName>CardVault</DisplayName>
    <PublisherDisplayName>{publisher_name}</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
    <Description>Secure, fully offline wallet for your bank cards.</Description>
  </Properties>

  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.26100.0" />
  </Dependencies>

  <Resources>
{resources}
  </Resources>

  <Applications>
    <Application Id="CardVault" Executable="CardVault.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements
        DisplayName="CardVault"
        Description="Secure, fully offline wallet for your bank cards."
        BackgroundColor="transparent"
        Square150x150Logo="Assets\\Square150x150Logo.png"
        Square44x44Logo="Assets\\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\\Wide310x150Logo.png" />
      </uap:VisualElements>
    </Application>
  </Applications>

  <!-- Singura capabilitate: rularea ca aplicație desktop clasică.
       NU se declară nicio capabilitate de rețea (internetClient, privateNetworkClientServer). -->
  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
"""


def msix_version(version: str) -> str:
    nums = [int(x) for x in re.findall(r"\d+", version)][:3]
    if len(nums) < 3:
        raise SystemExit(f"Versiune invalidă pentru MSIX: {version!r}")
    return f"{nums[0]}.{nums[1]}.{nums[2]}.0"   # Store cere ultima cifră 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--identity", required=True)
    ap.add_argument("--publisher", required=True)
    ap.add_argument("--publisher-name", required=True)
    ap.add_argument("--src", default=os.path.join(ROOT, "dist", "CardVault"))
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "msix"))
    a = ap.parse_args()

    if not a.publisher.startswith("CN="):
        raise SystemExit("--publisher trebuie să înceapă cu 'CN=' (copiat exact din Partner Center).")
    if not os.path.isfile(os.path.join(a.src, "CardVault.exe")):
        raise SystemExit(f"Nu găsesc {a.src}/CardVault.exe – rulează întâi build-ul.")

    if os.path.isdir(a.out):
        shutil.rmtree(a.out)
    shutil.copytree(a.src, a.out)
    assets = os.path.join(a.out, "Assets")
    os.makedirs(assets, exist_ok=True)
    for name in os.listdir(os.path.join(ROOT, "assets", "msix")):
        shutil.copy2(os.path.join(ROOT, "assets", "msix", name), assets)

    manifest = MANIFEST.format(
        identity=escape(a.identity, {'"': "&quot;"}),
        publisher=escape(a.publisher, {'"': "&quot;"}),
        publisher_name=escape(a.publisher_name),
        version=msix_version(a.version),
        resources="\n".join(f'    <Resource Language="{lang}" />' for lang in LANGS),
    )
    with open(os.path.join(a.out, "AppxManifest.xml"), "w", encoding="utf-8") as f:
        f.write(manifest)
    print(f"Conținut MSIX pregătit în {a.out} (versiune {msix_version(a.version)})")


if __name__ == "__main__":
    main()
