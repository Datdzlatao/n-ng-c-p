"""
app/core/security.py — Password hashing (PBKDF2-HMAC-SHA256) + JWT (PyJWT / RFC 7519)
Standard cryptographic implementations with timing attack defense and claim type validation.
"""
import hashlib
import hmac
import secrets
import time
import os
import jwt

from app.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRE_HOURS,
    PBKDF2_ITERATIONS,
    PBKDF2_HASH,
    JWT_REFRESH_EXPIRE_DAYS,
)


# ─────────────────────────────────────────────────
# PASSWORD HASHING (NIST PBKDF2-HMAC-SHA256)
# ─────────────────────────────────────────────────
def generate_salt(n_bytes: int = 16) -> str:
    return secrets.token_hex(n_bytes)


def hash_password(password: str, salt: str) -> str:
    """Return PBKDF2-HMAC-SHA256 hex digest."""
    dk = hashlib.pbkdf2_hmac(
        PBKDF2_HASH,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return dk.hex()


def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password, salt), stored_hash)


# ─────────────────────────────────────────────────
# JWT (PyJWT — RFC 7519 compliant)
# ─────────────────────────────────────────────────
def create_access_token(payload: dict) -> str:
    now = int(time.time())
    claims = {
        **payload,
        "iat": now,
        "exp": now + JWT_EXPIRE_HOURS * 3600,
        "type": "access",
    }
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """
    Returns decoded payload dict or None if invalid/expired.
    Validates that token type is access (prevents refresh token reuse).
    """
    try:
        claims = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat"]},
        )
        if claims.get("type") not in ("access", None):
            return None
        return claims
    except (jwt.PyJWTError, Exception):
        return None


# ─────────────────────────────────────────────────
# REFRESH TOKEN (JTI-based, revocable)
# ─────────────────────────────────────────────────
def create_refresh_token(user_id: int) -> tuple[str, str]:
    """Return (refresh_token_str, jti). Store jti in DB to allow revocation."""
    jti = secrets.token_urlsafe(32)
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "jti": jti,
        "type": "refresh",
        "iat": now,
        "exp": now + JWT_REFRESH_EXPIRE_DAYS * 86400,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, jti


def decode_refresh_token(token: str) -> dict | None:
    """Decode refresh token — enforces type=='refresh'."""
    try:
        claims = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat"]},
        )
        if claims.get("type") != "refresh":
            return None
        return claims
    except (jwt.PyJWTError, Exception):
        return None


def create_access_token_with_jti(payload: dict) -> tuple[str, str]:
    """Create access token with unique jti for tracking and blacklist support."""
    jti = secrets.token_urlsafe(16)
    now = int(time.time())
    exp = now + JWT_EXPIRE_HOURS * 3600
    claims = {
        **payload,
        "iat": now,
        "exp": exp,
        "jti": jti,
        "type": "access",
    }
    token = jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, jti

