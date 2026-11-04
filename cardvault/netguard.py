# CardVault - blocare totală a rețelei din interiorul aplicației
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
"""
CardVault nu are nevoie de rețea. Modulul acesta se activează primul la pornire
(în main.py) și oprește din interiorul procesului orice încercare de:

* conexiune la internet SAU la rețeaua locală (orice socket, inclusiv TCP/UDP),
* rezolvare de nume (DNS),
* lansare de alte programe (care ar putea ieși pe net în locul aplicației),
* încărcare prin ctypes a bibliotecilor Windows de rețea.

Se folosește un „audit hook” Python (PEP 578). Odată instalat, nu mai poate fi
dezinstalat până la închiderea aplicației. Orice tentativă ridică NetworkBlocked.

Limită (spusă sincer): cârligul acoperă codul Python. Bibliotecile native
(Qt, Windows) nu deschid conexiuni în CardVault, iar versiunea instalată cu
installer-ul adaugă în plus reguli Windows Firewall care blochează la nivel de
sistem orice trafic al CardVault.exe.
"""

import sys

__all__ = ["NetworkBlocked", "install", "is_active", "self_test"]


class NetworkBlocked(PermissionError):
    """Ridicată la orice încercare de acces la rețea din CardVault."""


# Evenimente de audit blocate (prefixe). Vezi lista oficială de evenimente Python.
_BLOCKED_PREFIXES = (
    "socket.",          # creare socket, connect, bind, sendto, DNS (getaddrinfo...)
    "urllib.",          # urllib.Request
    "http.",            # http.client.connect / send
    "ftplib.", "smtplib.", "imaplib.", "poplib.", "nntplib.", "telnetlib.",
    "webbrowser.",      # deschiderea browserului
    "subprocess.",      # alte programe ar putea ieși pe net
    "os.system", "os.exec", "os.spawn", "os.posix_spawn", "os.startfile",
)

# Singurele evenimente „socket.” permise: citirea numelui local al calculatorului
# (nu generează trafic).
_ALLOWED = {"socket.gethostname"}

# Biblioteci Windows de rețea care nu au voie să fie încărcate prin ctypes.
_NET_DLLS = ("ws2_32", "wsock32", "wininet", "winhttp", "urlmon", "iphlpapi",
             "dnsapi", "mswsock", "netapi32", "mpr", "rasapi32", "websocket")

_active = False


def _hook(event, args):
    if event in _ALLOWED:
        return
    if event.startswith(_BLOCKED_PREFIXES):
        raise NetworkBlocked(f"CardVault funcționează doar local – acțiune blocată: {event}")
    if event == "ctypes.dlopen" and args:
        name = str(args[0]).lower()
        if any(dll in name for dll in _NET_DLLS):
            raise NetworkBlocked(f"CardVault funcționează doar local – bibliotecă de rețea blocată: {name}")


def install():
    """Activează blocarea. Apelat o singură dată, la pornire."""
    global _active
    if _active:
        return
    sys.addaudithook(_hook)
    _active = True


def is_active() -> bool:
    return _active


def self_test() -> bool:
    """True dacă o încercare reală de conexiune este într-adevăr blocată."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except NetworkBlocked:
        return True
    s.close()
    return False
