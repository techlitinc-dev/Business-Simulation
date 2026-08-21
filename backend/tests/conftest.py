"""Shared pytest fixtures for the backend test suite."""

import os

# Tests must run without Postgres — force a shared-memory sqlite before any
# app module imports app.db.session. Both the module-level engine (StaticPool,
# which keeps one connection open so the in-memory DB persists) and worker tasks
# that build their own engine via settings.database_url attach to the SAME named
# in-memory DB, so per-task engines see the schema the fixture creates.
# Deliberately a hard assignment, not setdefault: inside Docker the compose file
# exports DATABASE_URL=postgresql+... and setdefault would leave it in place,
# letting the create_all/drop_all fixtures run against the real database.
os.environ["DATABASE_URL"] = (
    "sqlite+aiosqlite:///file:forge_test?mode=memory&cache=shared&uri=true"
)
# Cheap argon2 hashing keeps the test suite fast.
os.environ["FORGE_CHEAP_HASH"] = "1"

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import async_engine
from app.main import create_app
from app.workers.celery_app import celery_app
from httpx import ASGITransport, AsyncClient

# Run Celery tasks inline (no broker needed) in tests.
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = False


@pytest_asyncio.fixture(autouse=True)
async def _db_tables():
    """Create all tables on the shared sqlite engine before each test."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def app():
    """A fresh FastAPI app instance with a known (non-cached) settings override."""
    settings = get_settings()
    settings.debug = True
    settings.llm_api_key = ""  # deterministic mock provider mode
    settings.testing = True  # disable global rate limiter (T49); audit tests opt back in
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
