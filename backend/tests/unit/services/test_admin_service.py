"""Unit tests for admin_service aggregates (T46)."""


import pytest
from app.db.base import Base
from app.models.billing import Subscription, UsageRecord
from app.models.user import User
from app.models.workspace import Workspace
from app.services import admin_service
from app.services.metering_service import current_period
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


async def _workspace(db: AsyncSession, name: str = "W") -> Workspace:
    ws = Workspace(name=name, slug=f"{name.lower()}-1234", plan_tier="free")
    db.add(ws)
    await db.commit()
    return ws


async def test_mrr_estimate_uses_plan_prices(db: AsyncSession) -> None:
    ws1 = await _workspace(db, "A")
    ws2 = await _workspace(db, "B")
    db.add(Subscription(workspace_id=ws1.id, tier="pro", status="active"))
    db.add(Subscription(workspace_id=ws2.id, tier="enterprise", status="active"))
    # A canceled pro sub should NOT count.
    ws3 = await _workspace(db, "C")
    db.add(Subscription(workspace_id=ws3.id, tier="pro", status="canceled"))
    await db.commit()

    stats = await admin_service.admin_stats(db)
    assert stats.subscriptions_by_tier["pro"] == 1
    assert stats.subscriptions_by_tier["enterprise"] == 1
    assert stats.mrr_estimate_usd == 49 + 499


async def test_usage_aggregates_sum_current_period(db: AsyncSession) -> None:
    ws1 = await _workspace(db, "U1")
    ws2 = await _workspace(db, "U2")
    period = current_period()
    db.add(
        UsageRecord(
            workspace_id=ws1.id, period=period, runs_used=3, mc_ticks_used=10, llm_tokens_used=500
        )
    )
    db.add(
        UsageRecord(
            workspace_id=ws2.id, period=period, runs_used=2, mc_ticks_used=5, llm_tokens_used=300
        )
    )
    await db.commit()

    stats = await admin_service.admin_stats(db)
    assert stats.runs_this_month == 5
    assert stats.monte_carlo_ticks_this_month == 15
    assert stats.llm_tokens_this_month == 800


async def test_admin_users_search_case_insensitive(db: AsyncSession) -> None:
    for email in ("alice@b.co", "bob@b.co", "xalicey@b.co"):
        db.add(User(email=email, name="U", pw_hash="x"))
    await db.commit()

    result = await admin_service.admin_users(db, page=1, q="ALICE")
    assert result.total == 2
    assert {u.email for u in result.items} == {"alice@b.co", "xalicey@b.co"}


async def test_admin_workspaces_counts(db: AsyncSession) -> None:
    await _workspace(db, "Counts")
    result = await admin_service.admin_workspaces(db, page=1)
    assert result.total == 1
    assert result.items[0].name == "Counts"
    assert result.items[0].plan_tier == "free"
