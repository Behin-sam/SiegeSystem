"""
Core security utilities: JWT token creation, decoding, password hashing/verification,
and token hash generation for refresh token rotation.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    # bcrypt max is 72 bytes; truncate if needed
    pw_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt(BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))


def _create_token(
    subject: str,
    expires_delta: timedelta,
    token_type: Literal["access", "refresh", "mfa_challenge", "email_verify", "password_reset"],
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    return _create_token(
        subject,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
        extra,
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject,
        timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        "refresh",
    )


def create_extended_refresh_token(subject: str) -> str:
    """Used when 'remember_me' is enabled; extends refresh token lifetime."""
    return _create_token(
        subject,
        timedelta(days=30),
        "refresh",
    )


def create_mfa_challenge_token(subject: str) -> str:
    return _create_token(subject, timedelta(minutes=10), "mfa_challenge")


def create_email_verify_token(subject: str) -> str:
    return _create_token(subject, timedelta(hours=24), "email_verify")


def create_password_reset_token(subject: str) -> str:
    return _create_token(subject, timedelta(hours=1), "password_reset")


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """Hash a JWT or raw token for secure database storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_session_token() -> str:
    return secrets.token_urlsafe(64)
