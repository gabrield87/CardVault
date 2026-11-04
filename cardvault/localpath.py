# CardVault - regula „doar local” pentru fișiere
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
"""
Baza de date CardVault poate sta DOAR pe discurile acestui calculator
(inclusiv stick-uri/discuri USB). Sunt refuzate:

* căile de rețea \\\\server\\share (UNC),
* unitățile mapate din rețea (ex. Z: → \\\\server\\...),
* legăturile (symlink/junction) care duc în rețea.

În plus, detectăm folderele sincronizate cu servicii cloud (OneDrive, Google
Drive, Dropbox, iCloud...) ca să avertizăm utilizatorul: sincronizarea o face
acel serviciu, nu CardVault.
"""

import os
import sys

DRIVE_UNKNOWN, DRIVE_NO_ROOT_DIR, DRIVE_REMOVABLE, DRIVE_FIXED, DRIVE_REMOTE, DRIVE_CDROM, DRIVE_RAMDISK = range(7)


def _drive_type(root: str) -> int:
    import ctypes
    return ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))


def _existing_ancestor(path: str) -> str:
    p = os.path.abspath(path)
    while p and not os.path.exists(p):
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return p


def is_network_path(path: str) -> bool:
    """True dacă `path` duce (direct sau prin legături) într-o locație din rețea."""
    if not path:
        return True
    raw = str(path)
    checks = [raw]
    try:
        checks.append(os.path.realpath(_existing_ancestor(raw)))  # rezolvă symlink/junction
    except OSError:
        pass
    for p in checks:
        norm = p.replace("/", "\\")
        low = norm.lower()
        if low.startswith("\\\\?\\unc\\"):
            return True
        if low.startswith("\\\\.\\"):
            return True                      # căi de dispozitiv (pipe etc.) – refuzate
        if low.startswith("\\\\?\\"):
            norm = norm[4:]
            low = norm.lower()
            if low.startswith("unc\\"):
                return True
        if norm.startswith("\\\\"):
            return True                      # \\server\share
        if sys.platform == "win32":
            drive = os.path.splitdrive(os.path.abspath(norm))[0]
            if not drive:
                return True
            if drive.startswith("\\\\"):
                return True
            if _drive_type(drive + "\\") in (DRIVE_REMOTE, DRIVE_UNKNOWN, DRIVE_NO_ROOT_DIR):
                return True
    return False


_CLOUD_SEGMENTS = {
    "dropbox": "Dropbox",
    "google drive": "Google Drive",
    "my drive": "Google Drive",
    "googledrive": "Google Drive",
    "icloud drive": "iCloud",
    "iclouddrive": "iCloud",
    "box": "Box",
    "box sync": "Box",
    "pcloud drive": "pCloud",
    "mega": "MEGA",
}


def cloud_service(path: str):
    """Numele serviciului cloud dacă `path` e într-un folder sincronizat, altfel None."""
    full = os.path.normcase(os.path.abspath(path))
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        root = os.environ.get(var)
        if root and full.startswith(os.path.normcase(os.path.abspath(root)) + os.sep):
            return "OneDrive"
    parts = [p.lower() for p in os.path.abspath(path).replace("/", "\\").split("\\")]
    for part in parts:
        if part.startswith("onedrive"):
            return "OneDrive"
        if part in _CLOUD_SEGMENTS:
            return _CLOUD_SEGMENTS[part]
    return None


def is_packaged() -> bool:
    """True când rulează ca pachet MSIX (versiunea din Microsoft Store)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        length = ctypes.c_uint32(0)
        rc = ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
        return rc != 15700  # APPMODEL_ERROR_NO_PACKAGE
    except Exception:
        return False


def _first_local(candidates):
    for c in candidates:
        if c and not is_network_path(c):
            return c
    return None


def home_dir() -> str:
    return os.environ.get("USERPROFILE") or os.path.expanduser("~")


def default_vault_path() -> str:
    """Locația implicită a bazei de date: C:\\Users\\<utilizator>\\CardVault\\wallet.cvw.

    E vizibilă, locală, nu e sincronizată în cloud, nu e virtualizată de MSIX
    și nu se șterge la dezinstalare.
    """
    local = os.environ.get("LOCALAPPDATA") or os.path.join(home_dir(), ".local", "share")
    folder = _first_local([os.path.join(home_dir(), "CardVault"),
                           os.path.join(local, "CardVault")]) or os.path.join(home_dir(), "CardVault")
    return os.path.join(folder, "wallet.cvw")


def settings_dir() -> str:
    """Setările stau în %LOCALAPPDATA% (nu se sincronizează niciodată prin roaming)."""
    local = os.environ.get("LOCALAPPDATA") or os.path.join(home_dir(), ".config")
    return _first_local([os.path.join(local, "CardVault"),
                         os.path.join(home_dir(), "CardVault")]) or os.path.join(local, "CardVault")
