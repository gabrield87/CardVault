# CardVault - encrypted storage
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.
"""
Dedicated, password-protected SQLite database.

* The 256-bit encryption key is derived from the master password with scrypt
  (N=2^17, r=8, p=1) and a random 16-byte salt.
* Each card is serialised to JSON and encrypted individually with AES-256-GCM
  (random 12-byte nonce, card ID as associated data).
* Nothing about the cards is stored in plain text.
* The password itself is never stored; it is checked by decrypting a
  "verifier" block.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

SCHEMA_VERSION = 1
KDF_PARAMS = {"name": "scrypt", "n": 2 ** 17, "r": 8, "p": 1}
_VERIFIER = b"CardVault-verifier-v1"
_NONCE = 12


class VaultError(Exception):
    pass


class WrongPassword(VaultError):
    pass


def _derive_key(password: str, salt: bytes, params: dict) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=params["n"], r=params["r"], p=params["p"])
    return kdf.derive(password.encode("utf-8"))


def _encrypt(key: bytes, data: bytes, aad: bytes) -> bytes:
    nonce = os.urandom(_NONCE)
    return nonce + AESGCM(key).encrypt(nonce, data, aad)


def _decrypt(key: bytes, blob: bytes, aad: bytes) -> bytes:
    return AESGCM(key).decrypt(blob[:_NONCE], blob[_NONCE:], aad)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Vault:
    def __init__(self, path: str):
        self.path = path
        folder = os.path.dirname(os.path.abspath(path))
        os.makedirs(folder, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.execute("PRAGMA secure_delete = ON")
        with self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value BLOB NOT NULL)"
            )
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS cards (id TEXT PRIMARY KEY, blob BLOB NOT NULL)"
            )
        self._key = None

    @staticmethod
    def is_vault_file(path: str) -> bool:
        """READ-ONLY check whether the file is a CardVault database (never modifies it)."""
        if not os.path.isfile(path):
            return False
        try:
            uri = "file:" + os.path.abspath(path).replace("\\", "/") + "?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            try:
                row = conn.execute("SELECT value FROM meta WHERE key = 'verifier'").fetchone()
                conn.execute("SELECT id, blob FROM cards LIMIT 1")
                return row is not None
            finally:
                conn.close()
        except sqlite3.Error:
            return False

    # ---- meta ---------------------------------------------------------
    def _meta(self, key):
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def _set_meta(self, key, value):
        self._conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value)
        )

    # ---- state ----------------------------------------------------------
    def is_initialized(self) -> bool:
        return self._meta("verifier") is not None

    @property
    def unlocked(self) -> bool:
        return self._key is not None

    def _require_unlocked(self):
        if self._key is None:
            raise VaultError("vault is locked")

    def create(self, password: str):
        if self.is_initialized():
            raise VaultError("vault already exists")
        salt = os.urandom(16)
        key = _derive_key(password, salt, KDF_PARAMS)
        with self._conn:
            self._set_meta("schema", str(SCHEMA_VERSION))
            self._set_meta("kdf", json.dumps(KDF_PARAMS))
            self._set_meta("salt", salt)
            self._set_meta("verifier", _encrypt(key, _VERIFIER, b"verifier"))
        self._key = key

    def _check_password(self, password: str) -> bytes:
        params = json.loads(self._meta("kdf"))
        key = _derive_key(password, self._meta("salt"), params)
        try:
            if _decrypt(key, self._meta("verifier"), b"verifier") != _VERIFIER:
                raise WrongPassword()
        except InvalidTag:
            raise WrongPassword() from None
        return key

    def unlock(self, password: str):
        self._key = self._check_password(password)

    def lock(self):
        self._key = None

    # ---- cards ----------------------------------------------------------
    def list_cards(self) -> list:
        self._require_unlocked()
        cards = []
        for cid, blob in self._conn.execute("SELECT id, blob FROM cards"):
            data = json.loads(_decrypt(self._key, blob, cid.encode()))
            data["id"] = cid
            cards.append(data)
        cards.sort(key=lambda c: (c.get("label") or "").lower())
        return cards

    def save_card(self, card: dict) -> str:
        self._require_unlocked()
        card = dict(card)
        cid = card.pop("id", None) or uuid.uuid4().hex
        card.setdefault("created", _now())
        card["updated"] = _now()
        blob = _encrypt(self._key, json.dumps(card, ensure_ascii=False).encode("utf-8"), cid.encode())
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO cards (id, blob) VALUES (?, ?)", (cid, blob)
            )
        return cid

    def delete_card(self, cid: str):
        self._require_unlocked()
        with self._conn:
            self._conn.execute("DELETE FROM cards WHERE id = ?", (cid,))

    # ---- maintenance --------------------------------------------------------
    def change_password(self, old_password: str, new_password: str):
        old_key = self._check_password(old_password)
        rows = self._conn.execute("SELECT id, blob FROM cards").fetchall()
        plain = [(cid, _decrypt(old_key, blob, cid.encode())) for cid, blob in rows]
        salt = os.urandom(16)
        new_key = _derive_key(new_password, salt, KDF_PARAMS)
        with self._conn:  # single transaction: all or nothing
            self._set_meta("kdf", json.dumps(KDF_PARAMS))
            self._set_meta("salt", salt)
            self._set_meta("verifier", _encrypt(new_key, _VERIFIER, b"verifier"))
            for cid, data in plain:
                self._conn.execute(
                    "UPDATE cards SET blob = ? WHERE id = ?",
                    (_encrypt(new_key, data, cid.encode()), cid),
                )
        self._key = new_key

    def export(self, dest: str):
        """Exports a copy of the database (still encrypted with the same password)."""
        folder = os.path.dirname(os.path.abspath(dest))
        if folder:
            os.makedirs(folder, exist_ok=True)
        if os.path.abspath(dest) == os.path.abspath(self.path):
            raise VaultError("destination is the active database")
        target = sqlite3.connect(dest)
        try:
            self._conn.backup(target)
        finally:
            target.close()

    # backwards-compatible name
    backup = export

    def relocate(self, new_path: str):
        """Moves the database file to a new path, keeping the unlocked state.

        Copies the content to the new location, switches the connection to it and
        deletes the old file only after the move has succeeded.
        """
        new_path = os.path.abspath(new_path)
        old_path = os.path.abspath(self.path)
        if new_path == old_path:
            return
        folder = os.path.dirname(new_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        # write the new copy through a consistent backup of the current database
        target = sqlite3.connect(new_path)
        try:
            self._conn.backup(target)
        finally:
            target.close()
        # switch to the new file
        self._conn.close()
        self._conn = sqlite3.connect(new_path)
        self._conn.execute("PRAGMA secure_delete = ON")
        self.path = new_path
        # remove the old file (best effort)
        try:
            if os.path.exists(old_path):
                os.remove(old_path)
        except OSError:
            pass

    def close(self):
        self._key = None
        self._conn.close()
