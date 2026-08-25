"""Unit tests for the portfolio service (Day 25)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.db.base import Base
from app.models.portfolio import Portfolio, PortfolioMembership
from app.models.workspace import Workspace
from app.services.portfolio.portfolio_service import (
    add_workspace,
    create_portfolio,
    get_portfolio_summary,
    remove_workspace,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def test_get_portfolio_summary_returns_none_for_unknown() -> None:
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)
    result = await get_portfolio_summary("pf_unknown", db)
    assert result is None


async def test_get_portfolio_summary_sorts_by_score() -> None:
    portfolio = MagicMock()
    portfolio.id = "pf_001"
    portfolio.name = "Test Portfolio"
    portfolio.memberships = [
        MagicMock(workspace_id="ws_001", label="Company A"),
        MagicMock(workspace_id="ws_002", label="Company B"),
    ]

    # Run results: ws_001 has higher score (stored in result JSONB).
    run_a = MagicMock()
    run_a.result = {"survival_rate": 0.8, "resilience_score": 88}
    run_a.created_at = None
    run_b = MagicMock()
    run_b.result = {"survival_rate": 0.45, "resilience_score": 40}
    run_b.created_at = None

    db = AsyncMock()
    calls = [0]

    async def execute_mock(query: object) -> MagicMock:  # noqa: ARG001 - mocked execute
        mock = MagicMock()
        if calls[0] == 0:
            mock.scalar_one_or_none.return_value = portfolio
        elif calls[0] % 2 == 1:
            mock.scalar_one_or_none.return_value = run_a
        else:
            mock.scalar_one_or_none.return_value = run_b
        calls[0] += 1
        return mock

    db.execute = execute_mock

    result = await get_portfolio_summary("pf_001", db)
    assert result is not None
    assert result.workspaces[0].workspace_id == "ws_001"  # highest score first
    assert result.avg_resilience_score == 64.0  # (88 + 40) / 2


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def test_create_portfolio_persists_record(db: AsyncSession) -> None:
    owner_id = uuid.uuid4()
    portfolio = await create_portfolio("My Portfolio", owner_id, db)
    assert portfolio.id.startswith("pf_")

    fetched = await db.get(Portfolio, portfolio.id)
    assert fetched is not None
    assert fetched.name == "My Portfolio"
    assert fetched.owner_user_id == owner_id


async def test_add_workspace_creates_membership(db: AsyncSession) -> None:
    portfolio = await create_portfolio("P", uuid.uuid4(), db)
    ws = Workspace(name="W", slug=f"w-{uuid.uuid4().hex[:8]}")
    db.add(ws)
    await db.flush()

    membership = await add_workspace(portfolio.id, ws.id, "Company A", db)
    assert membership.id.startswith("pm_")

    fetched = await db.get(PortfolioMembership, membership.id)
    assert fetched is not None
    assert fetched.portfolio_id == portfolio.id
    assert fetched.workspace_id == ws.id
    assert fetched.label == "Company A"


async def test_remove_workspace_deletes_membership(db: AsyncSession) -> None:
    portfolio = await create_portfolio("P", uuid.uuid4(), db)
    ws = Workspace(name="W", slug=f"w-{uuid.uuid4().hex[:8]}")
    db.add(ws)
    await db.flush()
    membership = await add_workspace(portfolio.id, ws.id, "Company X", db)

    await remove_workspace(portfolio.id, ws.id, db)

    # The membership row is gone, but the workspace itself is untouched.
    assert await db.get(PortfolioMembership, membership.id) is None
    assert await db.get(Workspace, ws.id) is not None
