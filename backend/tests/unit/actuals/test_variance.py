"""Unit tests for the actuals variance computation (Day 13)."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.db.base import Base
from app.models.actuals import ActualsRecord
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.simulation import RunStatus, SimulationRun
from app.models.workspace import Workspace
from app.services.actuals.variance import compute_variance
from sqlalchemy.ext.asyncio import AsyncSession

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
_BLUEPRINT_PAYLOAD = json.loads((FIXTURES / "blueprint_golden.json").read_text())


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


async def _seed(db: AsyncSession) -> tuple[uuid.UUID, str]:
    ws = Workspace(name="W", slug=f"w-{uuid.uuid4().hex[:8]}")
    db.add(ws)
    await db.flush()
    bp = Blueprint(name="B", industry="tech", stage="seed", workspace_id=ws.id)
    db.add(bp)
    await db.flush()
    bpv = BlueprintVersion(
        blueprint_id=bp.id, version=1, payload=_BLUEPRINT_PAYLOAD, vulnerabilities=[]
    )
    db.add(bpv)
    await db.flush()
    run = SimulationRun(
        workspace_id=ws.id,
        blueprint_version_id=bpv.id,
        mode="monte_carlo",
        status=RunStatus.COMPLETED,
        seed=42,
        config={"n_runs": 20, "months": 24},
        result={
            "survival_rate": 0.9,
            "median_lifespan_months": 22.0,
            "resilience_score": 88,
            "runs_summary": [],
        },
    )
    db.add(run)
    await db.commit()
    return ws.id, bp.id


async def test_compute_variance_with_actuals(db: AsyncSession) -> None:
    ws_id, bp_id = await _seed(db)
    # Actuals that push churn up (worse for survival) vs. the blueprint's 5%.
    db.add(
        ActualsRecord(
            blueprint_id=bp_id,
            workspace_id=ws_id,
            month=3,
            fields={"revenue_engine.streams.0.churn_monthly": 0.09},
        )
    )
    await db.commit()

    result = await compute_variance(bp_id, ws_id, db, mc_runs=10)

    assert result.blueprint_id == bp_id
    assert result.month == 3
    # Prior metrics come from the seeded run result.
    assert result.prior_survival_rate == 0.9
    assert result.prior_runway_median == 22.0
    # Higher churn should not improve survival.
    assert result.survival_delta <= 0
    assert result.key_changes  # churn moved >5% vs the original payload
    assert any("churn_monthly" in c for c in result.key_changes)


async def test_compute_variance_no_actuals_raises(db: AsyncSession) -> None:
    ws_id, bp_id = await _seed(db)
    with pytest.raises(ValueError, match="No actuals"):
        await compute_variance(bp_id, ws_id, db)


async def test_compute_variance_key_changes_uses_original_payload(
    db: AsyncSession,
) -> None:
    """Fields equal to the blueprint's own values must NOT appear as changes."""
    ws_id, bp_id = await _seed(db)
    # churn 0.05 matches the blueprint exactly -> no key change for it.
    db.add(
        ActualsRecord(
            blueprint_id=bp_id,
            workspace_id=ws_id,
            month=1,
            fields={"revenue_engine.streams.0.churn_monthly": 0.05},
        )
    )
    await db.commit()

    result = await compute_variance(bp_id, ws_id, db, mc_runs=5)
    assert result.key_changes == []


async def test_compute_variance_mocked_no_actuals_raises() -> None:
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )
    )
    with pytest.raises(ValueError, match="No actuals"):
        await compute_variance("bp_001", uuid.uuid4(), mock_db)
