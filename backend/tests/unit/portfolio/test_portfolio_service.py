"""Unit tests for the portfolio service (Day 20)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.db.base import Base
from app.models.simulation import RunStatus, SimulationRun
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


async def test_create_add_remove_round_trip(db: AsyncSession) -> None:
    owner_id = uuid.uuid4()
    portfolio = await create_portfolio("My Portfolio", owner_id, db)
    assert portfolio.id.startswith("pf_")

    ws = Workspace(name="W", slug=f"w-{uuid.uuid4().hex[:8]}")
    db.add(ws)
    await db.flush()

    membership = await add_workspace(portfolio.id, ws.id, "Company X", db)
    assert membership.label == "Company X"

    summary = await get_portfolio_summary(portfolio.id, db)
    assert summary is not None
    assert summary.member_count == 1
    assert summary.workspaces[0].label == "Company X"
    # No completed runs yet -> no scores.
    assert summary.avg_resilience_score is None

    await remove_workspace(portfolio.id, ws.id, db)
    summary2 = await get_portfolio_summary(portfolio.id, db)
    assert summary2 is not None
    assert summary2.member_count == 0


async def test_summary_reads_latest_run_result(db: AsyncSession) -> None:
    portfolio = await create_portfolio("P", uuid.uuid4(), db)
    ws = Workspace(name="W", slug=f"w-{uuid.uuid4().hex[:8]}")
    db.add(ws)
    await db.flush()
    await add_workspace(portfolio.id, ws.id, "Company Y", db)

    from app.models.blueprint import Blueprint, BlueprintVersion

    bp = Blueprint(name="B", industry="tech", stage="seed", workspace_id=ws.id)
    db.add(bp)
    await db.flush()
    bpv = BlueprintVersion(blueprint_id=bp.id, version=1, payload={"x": 1}, vulnerabilities=[])
    db.add(bpv)
    await db.flush()
    run = SimulationRun(
        workspace_id=ws.id,
        blueprint_version_id=bpv.id,
        mode="monte_carlo",
        status=RunStatus.COMPLETED,
        seed=1,
        config={},
        result={"survival_rate": 0.7, "resilience_score": 72},
    )
    db.add(run)
    await db.commit()

    summary = await get_portfolio_summary(portfolio.id, db)
    assert summary is not None
    assert summary.workspaces[0].resilience_score == 72.0
    assert summary.workspaces[0].survival_rate == 0.7


async def test_two_workspaces_sorted_with_avg(db: AsyncSession) -> None:
    from app.models.blueprint import Blueprint, BlueprintVersion

    portfolio = await create_portfolio("Two Co", uuid.uuid4(), db)
    ws_a = Workspace(name="A", slug=f"w-{uuid.uuid4().hex[:8]}")
    ws_b = Workspace(name="B", slug=f"w-{uuid.uuid4().hex[:8]}")
    db.add_all([ws_a, ws_b])
    await db.flush()
    await add_workspace(portfolio.id, ws_a.id, "Company A", db)
    await add_workspace(portfolio.id, ws_b.id, "Company B", db)

    for ws, score, survival in ((ws_a, 88, 0.8), (ws_b, 40, 0.45)):
        bp = Blueprint(name="B", industry="tech", stage="seed", workspace_id=ws.id)
        db.add(bp)
        await db.flush()
        bpv = BlueprintVersion(
            blueprint_id=bp.id, version=1, payload={"x": 1}, vulnerabilities=[]
        )
        db.add(bpv)
        await db.flush()
        db.add(
            SimulationRun(
                workspace_id=ws.id,
                blueprint_version_id=bpv.id,
                mode="monte_carlo",
                status=RunStatus.COMPLETED,
                seed=1,
                config={},
                result={"survival_rate": survival, "resilience_score": score},
            )
        )
    await db.commit()

    summary = await get_portfolio_summary(portfolio.id, db)
    assert summary is not None
    assert summary.member_count == 2
    assert [w.workspace_id for w in summary.workspaces] == [str(ws_a.id), str(ws_b.id)]
    assert summary.workspaces[0].resilience_score == 88.0
    assert summary.avg_resilience_score == 64.0  # (88 + 40) / 2
