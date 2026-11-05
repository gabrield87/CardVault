# CardVault - "local only" rule for files
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
"""
The CardVault database may live ONLY on this computer's drives
(USB sticks/drives included). Rejected:

* network paths \\\\server\\share (UNC),
* drives mapped from the network (e.g. Z: -> \\\\server\\...),
* links (symlink/junction) that lead to the network.

We also detect folders synced by cloud services (OneDrive, Google Drive,
Dropbox, iCloud...) to warn the user: that service does the syncing, not
CardVault.
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
    """True if `path` leads (directly or through links) to a network location."""
    if not path:
        return True
    raw = str(path)
    checks = [raw]
    try:
        checks.append(os.path.realpath(_existing_ancestor(raw)))  # resolves symlinks/junctions
    except OSError:
        pass
    for p in checks:
        norm = p.replace("/", "\\")
        low = norm.lower()
        if low.startswith("\\\\?\\unc\\"):
            return True
        if low.startswith("\\\\.\\"):
            return True                      # device paths (pipes etc.) - rejected
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
    """Name of the cloud service if `path` is in a synced folder, otherwise None."""
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
    """True when running as an MSIX package (the Microsoft Store version)."""
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
    """Default database location: C:\\Users\\<user>\\CardVault\\wallet.cvw.

    Visible, local, not synced to the cloud, not virtualised by MSIX and not
    deleted on uninstall.
    """
    local = os.environ.get("LOCALAPPDATA") or os.path.join(home_dir(), ".local", "share")
    folder = _first_local([os.path.join(home_dir(), "CardVault"),
                           os.path.join(local, "CardVault")]) or os.path.join(home_dir(), "CardVault")
    return os.path.join(folder, "wallet.cvw")


def settings_dir() -> str:
    """Settings live in %LOCALAPPDATA% (never synced through roaming profiles)."""
    local = os.environ.get("LOCALAPPDATA") or os.path.join(home_dir(), ".config")
    return _first_local([os.path.join(local, "CardVault"),
                         os.path.join(home_dir(), "CardVault")]) or os.path.join(local, "CardVault")
