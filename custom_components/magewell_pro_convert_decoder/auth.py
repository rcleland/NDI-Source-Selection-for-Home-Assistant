"""Magewell mwapi login (MD5 password, session cookie)."""

from __future__ import annotations

import hashlib


def password_md5_hex(plain: str) -> str:
    """API expects pass= MD5 hex digest of the password (see login docs)."""
    return hashlib.md5(plain.encode("utf-8")).hexdigest()
