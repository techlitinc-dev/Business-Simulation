"""Password hashing (argon2) and JWT token creation/decoding."""

import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext  # type: ignore[import-untyped]

from app.core.config import get_settings

# Lower-cost argon2 for tests (conftest sets FORGE_CHEAP_HASH); production uses
# the argon2 library defaults (memory_cost=64 MiB, time_cost=3).
_cheap = get_settings().debug or os.environ.get("FORGE_CHEAP_HASH") == "1"
if _cheap:
    pwd_context: CryptContext = CryptContext(
        schemes=["argon2"],
        deprecated="auto",
        argon2__memory_cost=16 * 1024,  # 16 MiB
        argon2__time_cost=1,
        argon2__parallelism=1,
    )
else:
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return str(pwd_context.hash(password))


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bool(pwd_context.verify(password, password_hash))
    except ValueError:
        # Malformed or unsupported hash — treat as invalid.
        return False


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "type": "access",
        "jti": secrets.token_urlsafe(16),
        "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
        "exp": datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a token; raises jwt.PyJWTError on expiry/invalid."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
