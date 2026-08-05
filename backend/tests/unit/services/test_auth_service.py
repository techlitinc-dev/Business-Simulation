"""Unit tests for auth service: hashing, tokens, service functions."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.base import Base
from app.services import auth_service
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture
async def db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def test_hash_roundtrip() -> None:
    h = hash_password("s3cret!")
    assert h.startswith("$argon2")
    assert verify_password("s3cret!", h)
    assert not verify_password("wrong", h)


def test_verify_password_rejects_garbage() -> None:
    assert verify_password("pw", "not-a-hash") is False


def test_access_token_claims() -> None:
    token = create_access_token("user-1")
    claims = decode_token(token)
    assert claims["sub"] == "user-1"
    assert claims["type"] == "access"
    assert "exp" in claims


def test_refresh_token_claims() -> None:
    token = create_refresh_token("user-1")
    claims = decode_token(token)
    assert claims["sub"] == "user-1"
    assert claims["type"] == "refresh"


def test_decode_expired_token_raises() -> None:
    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": "u",
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired)


async def test_register_and_authenticate(db: AsyncSession) -> None:
    user = await auth_service.register_user(
        db, email="Svc@Ex.com", name="Svc", password="password123"
    )
    assert user.email == "svc@ex.com"
    assert user.pw_hash.startswith("$argon2")

    authed = await auth_service.authenticate_user(
        db, email="svc@ex.com", password="password123"
    )
    assert authed.id == user.id


async def test_register_duplicate_raises_409(db: AsyncSession) -> None:
    await auth_service.register_user(
        db, email="d@b.co", name="D", password="password123"
    )
    with pytest.raises(DomainError) as exc_info:
        await auth_service.register_user(
            db, email="d@b.co", name="D2", password="password123"
        )
    assert exc_info.value.status_code == 409


async def test_authenticate_wrong_password_raises_401(db: AsyncSession) -> None:
    await auth_service.register_user(
        db, email="w@b.co", name="W", password="password123"
    )
    with pytest.raises(DomainError) as exc_info:
        await auth_service.authenticate_user(db, email="w@b.co", password="nope")
    assert exc_info.value.status_code == 401


async def test_refresh_tokens_rotates_pair(db: AsyncSession) -> None:
    user = await auth_service.register_user(
        db, email="t@b.co", name="T", password="password123"
    )
    old_refresh = create_refresh_token(str(user.id))
    pair = auth_service.refresh_tokens(db, old_refresh)
    assert pair.access_token
    assert pair.refresh_token != old_refresh


async def test_refresh_rejects_access_token(db: AsyncSession) -> None:
    user = await auth_service.register_user(
        db, email="a@b.co", name="A", password="password123"
    )
    access = create_access_token(str(user.id))
    with pytest.raises(DomainError) as exc_info:
        auth_service.refresh_tokens(db, access)
    assert exc_info.value.status_code == 401
