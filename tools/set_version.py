# CardVault - injectează versiunea în aplicație la build
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
#
# Scrie:
#   cardvault/_version.py   -> versiunea citită de aplicație
#   version_info.txt        -> metadatele din CardVault.exe (Proprietăți → Detalii)
#
# Versiunea se ia, în ordine, din:
#   1) argument în linia de comandă:  python tools/set_version.py 1.4.0
#   2) variabila de mediu GITHUB_REF_NAME (tag-ul Release, ex. "v1.4.0")
#   3) variabila de mediu CARDVAULT_VERSION
# Apelat automat de workflow-ul GitHub la publicarea unui Release.

import os
import re
import sys
from datetime import date

AUTHOR = "Gabriel Dobre"
APP_NAME = "CardVault"
COPYRIGHT_START_YEAR = 2026
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_version() -> str:
    raw = (
        (sys.argv[1] if len(sys.argv) > 1 else "")
        or os.environ.get("GITHUB_REF_NAME", "")
        or os.environ.get("CARDVAULT_VERSION", "")
    ).strip()
    raw = re.sub(r"^v", "", raw, flags=re.IGNORECASE)  # "v1.4.0" -> "1.4.0"
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", raw)
    if not m:
        raise SystemExit(
            f"Versiune invalidă: {raw!r}. Aștept ceva de forma 1.4.0 (sau tag v1.4.0)."
        )
    return raw


def four_tuple(version: str):
    nums = [int(x) for x in re.findall(r"\d+", version)][:4]
    while len(nums) < 4:
        nums.append(0)
    return tuple(nums[:4])


def copyright_year() -> str:
    y = date.today().year
    return str(COPYRIGHT_START_YEAR) if y <= COPYRIGHT_START_YEAR else f"{COPYRIGHT_START_YEAR}-{y}"


def write_version_module(version: str):
    path = os.path.join(ROOT, "cardvault", "_version.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Generat automat de tools/set_version.py. Nu edita manual.\n")
        f.write(f'__version__ = "{version}"\n')
    print("scris", path)


def write_version_info(version: str):
    vt = four_tuple(version)
    copyright_txt = f"© {copyright_year()} {AUTHOR}. All rights reserved."
    content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers={vt}, prodvers={vt}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{AUTHOR}'),
      StringStruct('FileDescription', '{APP_NAME} - secure bank card wallet'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', '{APP_NAME}'),
      StringStruct('LegalCopyright', '{copyright_txt}'),
      StringStruct('OriginalFilename', '{APP_NAME}.exe'),
      StringStruct('ProductName', '{APP_NAME}'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    path = os.path.join(ROOT, "version_info.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("scris", path)


def main():
    version = resolve_version()
    write_version_module(version)
    write_version_info(version)
    print(f"Versiune aplicată: {version}")


if __name__ == "__main__":
    main()
