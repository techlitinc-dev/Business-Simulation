"""Unit tests for the API key service (T45)."""

import hashlib

import pytest
from app.db.base import Base
from app.models.api_key import ApiKey
from app.models.workspace import Workspace
from app.services import api_key_service
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


async def test_create_api_key_returns_plaintext_once(db: AsyncSession) -> None:
    ws = Workspace(name="A", slug="a-1234", plan_tier="enterprise")
    db.add(ws)
    await db.commit()

    response, _ = await api_key_service.create_api_key(
        db,
        workspace_id=ws.id,
        name="CI",
        scopes=["runs:read", "reports:read"],
        rate_limit_rpm=120,
    )
    assert response.key.startswith("fk_")
    assert response.prefix == response.key[:12]
    assert response.id.startswith("key_")

    # DB stores only prefix + hash — no plaintext.
    stored = await db.get(ApiKey, response.id)
    assert stored.key_hash == hashlib.sha256(response.key.encode()).hexdigest()
    assert stored.key_hash != response.key
    assert stored.prefix == response.key[:12]


async def test_list_api_keys_excludes_hash(db: AsyncSession) -> None:
    ws = Workspace(name="B", slug="b-1234", plan_tier="enterprise")
    db.add(ws)
    await db.commit()

    await api_key_service.create_api_key(
        db, workspace_id=ws.id, name="K1", scopes=["runs:read"], rate_limit_rpm=60
    )
    keys = await api_key_service.list_api_keys(db, workspace_id=ws.id)
    assert len(keys) == 1
    assert not hasattr(keys[0], "key_hash")
    assert not hasattr(keys[0], "key")


async def test_revoke_api_key(db: AsyncSession) -> None:
    ws = Workspace(name="C", slug="c-1234", plan_tier="enterprise")
    db.add(ws)
    await db.commit()

    response, _ = await api_key_service.create_api_key(
        db, workspace_id=ws.id, name="K2", scopes=["runs:read"], rate_limit_rpm=60
    )
    await api_key_service.revoke_api_key(
        db, workspace_id=ws.id, api_key_id=response.id
    )

    # Revoked keys no longer authenticate.
    key = await api_key_service.find_active_key(db, response.key)
    assert key is None


async def test_find_active_key_updates_last_used(db: AsyncSession) -> None:
    ws = Workspace(name="D", slug="d-1234", plan_tier="enterprise")
    db.add(ws)
    await db.commit()

    response, _ = await api_key_service.create_api_key(
        db, workspace_id=ws.id, name="K3", scopes=["runs:read"], rate_limit_rpm=60
    )
    key = await api_key_service.find_active_key(db, response.key)
    assert key is not None
    assert key.last_used_at is not None


async def test_unknown_key_returns_none(db: AsyncSession) -> None:
    key = await api_key_service.find_active_key(db, "fk_unknown")
    assert key is None
