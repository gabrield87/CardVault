# CardVault
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
#
# Informațiile de identitate ale aplicației se definesc O SINGURĂ DATĂ aici.
# Nu le mai schimba manual în altă parte:
#   - anul de copyright se actualizează automat (anul curent);
#   - versiunea este injectată la build din Release-ul de pe GitHub
#     (fișierul cardvault/_version.py, generat de workflow / tools/set_version.py).

from datetime import date as _date

APP_NAME = "CardVault"
AUTHOR = "Gabriel Dobre"
COPYRIGHT_HOLDER = AUTHOR

# Anul din care există dreptul de autor. Afișarea se extinde automat ca interval
# (ex. „2026–2027”) pe măsură ce trece timpul, fără nicio intervenție.
COPYRIGHT_START_YEAR = 2026


def _copyright_year() -> str:
    y = _date.today().year
    if y <= COPYRIGHT_START_YEAR:
        return str(COPYRIGHT_START_YEAR)
    return f"{COPYRIGHT_START_YEAR}–{y}"


def copyright_line() -> str:
    """Textul complet de copyright, calculat la momentul rulării."""
    return f"© {_copyright_year()} {COPYRIGHT_HOLDER}. All rights reserved."


def copyright_short() -> str:
    return f"© {_copyright_year()} {COPYRIGHT_HOLDER}"


# Versiunea: injectată la build. Implicit „dev” când rulezi direct din sursă.
try:
    from ._version import __version__ as APP_VERSION
except Exception:
    APP_VERSION = "0.0.0-dev"

# Valori dinamice pentru compatibilitate cu codul existent.
COPYRIGHT_YEAR = _copyright_year()
COPYRIGHT = copyright_short()
