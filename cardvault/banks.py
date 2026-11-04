# CardVault - issuing banks
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
"""
Băncile emitente acceptate și tema vizuală a fiecăreia.

Pentru a adăuga o bancă nouă, adaugă o intrare în BANKS.

Siglele oficiale sunt mărci înregistrate ale băncilor și nu sunt incluse în
aplicație. Pentru a le afișa pe carduri, pune fișierul PNG (fundal transparent)
în folderul `banks` de lângă CardVault.exe, cu numele `<id>.png`
(ex. `banks\\ing.png`). Fără fișier, pe card apare numele băncii.
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
    "revolut": ("revolut",),
}


def bank(bank_id: str) -> dict:
    return BANKS.get(bank_id or "", _UNKNOWN)


def guess_bank_id(text: str) -> str:
    """Pentru carduri salvate de versiunea 1.0 (banca era text liber)."""
    words = (text or "").lower().replace("-", " ").replace("–", " ").split()
    for bid, keys in _KEYWORDS.items():
        if any(k in words or (len(k) > 3 and k in (text or "").lower()) for k in keys):
            return bid
    return ""


def logo_path(bank_id: str):
    """Caută siglele lângă executabil (banks\\<id>.png), apoi în resursele aplicației."""
    if not bank_id:
        return None
    if getattr(sys, "frozen", False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    candidates = [os.path.join(app_dir, "banks", f"{bank_id}.png"),
                  # folder editabil și în versiunea din Store (unde folderul aplicației e doar-citire)
                  os.path.join(home, "CardVault", "banks", f"{bank_id}.png")]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, "assets", "banks", f"{bank_id}.png"))
    candidates.append(os.path.join(app_dir, "assets", "banks", f"{bank_id}.png"))
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None
