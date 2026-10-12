"""Password hashing, login tokens and role permissions."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from .config import get_settings

_ph = PasswordHasher()
TOKEN_HOURS = 12
ALGORITHM = "HS256"

# Permission matrix. Keep this the single source of truth: the API, the UI and the
# tests all read it.
PERMISSIONS: dict[str, set[str]] = {
    "sources.view": {"admin", "geologist", "analyst"},
    "sources.register_inbox": {"admin", "geologist", "analyst"},
    "layers.view_all": {"admin", "geologist", "analyst"},
    "map.view": {"admin", "geologist", "analyst", "investor"},
    "rescue.upload": {"admin", "geologist", "analyst"},
    "rescue.view": {"admin", "geologist", "analyst"},
    "facts.review": {"admin", "geologist"},
    "model.run": {"admin", "geologist", "analyst"},
    "model.view": {"admin", "geologist", "analyst"},
    "model.edit_weights": {"admin", "geologist"},
    "claims.create": {"admin", "geologist", "analyst", "miner"},
    "dataroom.view": {"admin", "geologist", "analyst", "investor"},
    "dataroom.download": {"admin", "geologist", "analyst", "investor"},
    "dataroom.share": {"admin"},
    "audit.view": {"admin"},
    "users.manage": {"admin"},
    "demo.control": {"admin"},
}

ROLE_LABELS = {
    "admin": "Admin",
    "geologist": "Geologist",
    "analyst": "Analyst",
    "investor": "Investor",
    "miner": "Miner",
}


def can(role: str, permission: str) -> bool:
    return role in PERMISSIONS.get(permission, set())


def permissions_for(role: str) -> list[str]:
    return sorted(p for p, roles in PERMISSIONS.items() if role in roles)


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, pw)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def _secret() -> str:
    key = get_settings().secret_key
    if not key or key == "change-me":
        # Prototype fallback: a per-process random key. Tokens then expire on restart.
        global _EPHEMERAL
        if _EPHEMERAL is None:
            _EPHEMERAL = secrets.token_urlsafe(32)
        return _EPHEMERAL
    return key


_EPHEMERAL: str | None = None


def create_token(username: str, role: str) -> str:
    now = datetime.now(UTC)
    payload = {"sub": username, "role": role, "iat": now, "exp": now + timedelta(hours=TOKEN_HOURS)}
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=[ALGORITHM])
