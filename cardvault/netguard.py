# CardVault - complete network lockdown from inside the application
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
"""
CardVault does not need the network. This module is enabled first at startup
(in main.py) and blocks, from inside the process, any attempt to:

* connect to the internet OR the local network (any socket, TCP/UDP included),
* resolve names (DNS),
* launch other programs (which could reach the network on the app's behalf),
* load Windows networking libraries through ctypes.

It uses a Python audit hook (PEP 578). Once installed it cannot be removed until
the application exits. Every attempt raises NetworkBlocked.

Limitation (stated honestly): the hook covers Python code. Native libraries
(Qt, Windows) do not open connections in CardVault, and the installed version
additionally adds Windows Firewall rules that block, system-wide, all traffic
of CardVault.exe.
"""

import sys

__all__ = ["NetworkBlocked", "install", "is_active", "self_test"]


class NetworkBlocked(PermissionError):
    """Raised on any attempt to access the network from CardVault."""


# Blocked audit events (prefixes). See the official list of Python audit events.
_BLOCKED_PREFIXES = (
    "socket.",          # socket creation, connect, bind, sendto, DNS (getaddrinfo...)
    "urllib.",          # urllib.Request
    "http.",            # http.client.connect / send
    "ftplib.", "smtplib.", "imaplib.", "poplib.", "nntplib.", "telnetlib.",
    "webbrowser.",      # opening the web browser
    "subprocess.",      # other programs could reach the network
    "os.system", "os.exec", "os.spawn", "os.posix_spawn", "os.startfile",
)

# The only "socket." event allowed: reading the local computer name
# (generates no traffic).
_ALLOWED = {"socket.gethostname"}

# Windows networking libraries that must not be loaded through ctypes.
_NET_DLLS = ("ws2_32", "wsock32", "wininet", "winhttp", "urlmon", "iphlpapi",
             "dnsapi", "mswsock", "netapi32", "mpr", "rasapi32", "websocket")

_active = False


def _hook(event, args):
    if event in _ALLOWED:
        return
    if event.startswith(_BLOCKED_PREFIXES):
        raise NetworkBlocked(f"CardVault works locally only - blocked action: {event}")
    if event == "ctypes.dlopen" and args:
        name = str(args[0]).lower()
        if any(dll in name for dll in _NET_DLLS):
            raise NetworkBlocked(f"CardVault works locally only - blocked network library: {name}")


def install():
    """Enables the lockdown. Called once, at startup."""
    global _active
    if _active:
        return
    sys.addaudithook(_hook)
    _active = True


def is_active() -> bool:
    return _active


def self_test() -> bool:
    """True if a real connection attempt is actually blocked."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except NetworkBlocked:
        return True
    s.close()
    return False
