# CardVault - issuing banks
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
"""
Supported issuing banks and the visual theme of each one.

To add a new bank, add an entry to BANKS.

Official logos are registered trademarks of the banks and are not shipped with
the app. To show them on cards, put a PNG file (transparent background) named
`<id>.png` in the `banks` folder next to CardVault.exe (e.g. `banks\\ing.png`),
or in `%USERPROFILE%\\CardVault\\banks`. Without a file, the bank name is shown.
"""

import os
import sys

BANKS = {
    "ing": {
        "name": "ING Bank",
        "short": "ING",
        "colors": ("#FF6200", "#D94A00"),
        "text": "#FFFFFF",
        "accent": "#000066",
    },
    "bt": {
        "name": "Banca Transilvania",
        "short": "BT",
        "colors": ("#FFD200", "#F2A900"),
        "text": "#1D1D1B",
        "accent": "#003B71",
    },
    "brd": {
        "name": "BRD – Groupe Société Générale",
        "short": "BRD",
        "colors": ("#E9041E", "#1A1A1A"),
        "text": "#FFFFFF",
        "accent": "#000000",
    },
    "cec": {
        "name": "CEC Bank",
        "short": "CEC Bank",
        "mini": "CEC",
        "colors": ("#037541", "#01492A"),
        "text": "#FFFFFF",
        "accent": "#F8E872",
    },
    "raiffeisen": {
        "name": "Raiffeisen Bank",
        "short": "Raiffeisen",
        "mini": "RAIFF",
        "colors": ("#FFE100", "#D9A300"),   # golden yellow
        "text": "#000000",                   # black text
        "accent": "#000000",                 # black accents
        "deco_alpha": 70,                    # stronger black decorative circle
    },
    "revolut": {
        "name": "Revolut",
        "short": "Revolut",
        "colors": ("#191C1F", "#454B55"),
        "text": "#FFFFFF",
        "accent": "#FFFFFF",
    },
}

BANK_IDS = list(BANKS.keys())

_UNKNOWN = {
    "name": "",
    "short": "",
    "colors": ("#3a4256", "#232838"),
    "text": "#FFFFFF",
    "accent": "#FFFFFF",
}

_KEYWORDS = {
    "ing": ("ing",),
    "bt": ("bt", "transilvania"),
    "brd": ("brd", "societe", "société"),
    "cec": ("cec",),
    "raiffeisen": ("raiffeisen", "raif"),
    "revolut": ("revolut",),
}


def bank(bank_id: str) -> dict:
    return BANKS.get(bank_id or "", _UNKNOWN)


def guess_bank_id(text: str) -> str:
    """For cards saved by version 1.0 (the bank was free text)."""
    words = (text or "").lower().replace("-", " ").replace("–", " ").split()
    for bid, keys in _KEYWORDS.items():
        if any(k in words or (len(k) > 3 and k in (text or "").lower()) for k in keys):
            return bid
    return ""


def logo_path(bank_id: str):
    """Looks for logos next to the executable (banks\\<id>.png), then in other known places."""
    if not bank_id:
        return None
    if getattr(sys, "frozen", False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    candidates = [os.path.join(app_dir, "banks", f"{bank_id}.png"),
                  # user-editable folder, also for the Store build (where the app folder is read-only)
                  os.path.join(home, "CardVault", "banks", f"{bank_id}.png")]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, "assets", "banks", f"{bank_id}.png"))
    candidates.append(os.path.join(app_dir, "assets", "banks", f"{bank_id}.png"))
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None
