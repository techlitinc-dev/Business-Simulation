"""Unit tests for the metering service (T41)."""

import pytest
from app.core.exceptions import PlanLimitExceeded
from app.db.base import Base
from app.models.billing import UsageRecord
from app.models.workspace import Workspace
from app.services import metering_service
from sqlalchemy import select
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


async def _workspace(db: AsyncSession, tier: str = "free") -> Workspace:
    ws = Workspace(name="M", slug="m-1234", plan_tier=tier)
    db.add(ws)
    await db.commit()
    return ws


async def test_get_current_usage_creates_row(db: AsyncSession) -> None:
    ws = await _workspace(db)
    record = await metering_service.get_current_usage(db, ws.id)
    assert record.period == metering_service.current_period()
    assert record.runs_used == 0
    assert record.mc_ticks_used == 0
    assert record.llm_tokens_used == 0


async def test_increment_updates_counters(db: AsyncSession) -> None:
    ws = await _workspace(db)
    await metering_service.increment(db, ws.id, "runs", amount=2)
    await metering_service.increment(db, ws.id, "llm_tokens", amount=150)
    record = await db.scalar(
        select(UsageRecord).where(UsageRecord.workspace_id == ws.id)
    )
    assert record is not None
    assert record.runs_used == 2
    assert record.llm_tokens_used == 150


async def test_check_limit_unlimited_tier_passes(db: AsyncSession) -> None:
    ws = await _workspace(db, tier="enterprise")
    # enterprise limits are -1 (unlimited) — no exception.
    await metering_service.check_limit(db, ws.id, "runs", amount=1000)


async def test_check_limit_raises_when_exceeded(db: AsyncSession) -> None:
    ws = await _workspace(db, tier="free")  # free: 3 runs/mo
    await metering_service.increment(db, ws.id, "runs", amount=3)
    with pytest.raises(PlanLimitExceeded) as exc:
        await metering_service.check_limit(db, ws.id, "runs", amount=1)
    assert exc.value.metric == "runs"
    assert exc.value.limit == 3
    assert exc.value.used == 3
    assert exc.value.tier == "free"


async def test_check_limit_allows_under_limit(db: AsyncSession) -> None:
    ws = await _workspace(db, tier="free")
    await metering_service.increment(db, ws.id, "runs", amount=2)
    # Should not raise.
    await metering_service.check_limit(db, ws.id, "runs", amount=1)
