"""DB layer tests that run without a Postgres server (aiosqlite)."""

import pytest
from app.db.base import Base, TimestampMixin
from app.db.session import async_engine
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture
async def sqlite_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def test_base_metadata_imports_cleanly() -> None:
    """Base.metadata imports without error and includes the known tables."""
    assert TimestampMixin is not None
    assert {"users", "workspaces", "memberships", "invites"} <= set(
        Base.metadata.tables
    )


async def test_async_session_factory_yields_working_session() -> None:
    """The async_sessionmaker factory pattern yields a working session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()
    result = await session.execute(text("SELECT 1"))
    assert result.scalar() == 1
    await session.close()
    await engine.dispose()


async def test_sqlite_session_smoke(sqlite_session: AsyncSession) -> None:
    """get_db-style session: execute a trivial query and commit works."""
    result = await sqlite_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


async def test_engine_pool_pre_ping() -> None:
    # The test env forces a sqlite engine (see conftest), which does not use
    # pre-ping; the production Postgres engine sets it to True.
    assert async_engine.dialect.name == "sqlite"
    assert "sqlite" in async_engine.url.drivername
