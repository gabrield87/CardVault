# CardVault - card helpers
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.

import re
from datetime import date, timedelta

# (c1, c2) gradient presets
COLORS = [
    ("#1e3c72", "#2a5298"),  # albastru
    ("#141e30", "#35577d"),  # bleumarin
    ("#0f2027", "#2c5364"),  # petrol
    ("#11998e", "#38ef7d"),  # verde
    ("#8e2de2", "#4a00e0"),  # violet
    ("#c31432", "#240b36"),  # roșu
    ("#f7971e", "#c0392b"),  # portocaliu
    ("#232526", "#414345"),  # negru
    ("#b8860b", "#5c4300"),  # auriu
    ("#606c88", "#3f4c6b"),  # argintiu
]


def digits(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def luhn_ok(number: str) -> bool:
    n = digits(number)
    if not n:
        return False
    total = 0
    for i, ch in enumerate(reversed(n)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def detect_brand(number: str) -> str:
    n = digits(number)
    if not n:
        return ""
    p2 = int(n[:2]) if len(n) >= 2 else -1
    p3 = int(n[:3]) if len(n) >= 3 else -1
    p4 = int(n[:4]) if len(n) >= 4 else -1
    if p2 in (34, 37):
        return "American Express"
    if 300 <= p3 <= 305 or p2 in (36, 38, 39):
        return "Diners Club"
    if 3528 <= p4 <= 3589:
        return "JCB"
    if p4 == 6011 or p2 == 65 or 644 <= p3 <= 649:
        return "Discover"
    if p2 == 62:
        return "UnionPay"
    if 51 <= p2 <= 55 or 2221 <= p4 <= 2720:
        return "Mastercard"
    if n[0] == "4":
        return "Visa"
    if p2 in (50, 56, 57, 58) or p2 in (63, 67, 68, 69):
        return "Maestro"
    return ""


def format_number(number: str) -> str:
    n = digits(number)
    if detect_brand(n) == "American Express":
        parts = [n[:4], n[4:10], n[10:15], n[15:]]
    else:
        parts = [n[i:i + 4] for i in range(0, len(n), 4)]
    return " ".join(p for p in parts if p)


def mask_number(number: str) -> str:
    n = digits(number)
    if len(n) < 4:
        return "••••"
    return "•••• •••• •••• " + n[-4:]


def parse_expiry(text: str):
    """'MM/YY' -> (month, year) sau None."""
    m = re.fullmatch(r"\s*(\d{1,2})\s*/\s*(\d{2}|\d{4})\s*", text or "")
    if not m:
        return None
    month, year = int(m.group(1)), int(m.group(2))
    if not 1 <= month <= 12:
        return None
    if year < 100:
        year += 2000
    return month, year


def expiry_last_day(text: str):
    """Ultima zi în care cardul mai este valabil (ultima zi a lunii de expirare)."""
    parsed = parse_expiry(text)
    if not parsed:
        return None
    month, year = parsed
    return date(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1)


def days_left(text: str, today: date = None):
    last = expiry_last_day(text)
    if last is None:
        return None
    return (last - (today or date.today())).days


def expiry_status(text: str, soon_days: int = 60, today: date = None) -> str:
    """'expired', 'soon', 'ok' sau '' dacă data lipsește."""
    left = days_left(text, today)
    if left is None:
        return ""
    if left < 0:
        return "expired"
    if left <= soon_days:
        return "soon"
    return "ok"
