"""Unit tests for the actuals variance computation (Day 13)."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from app.agents.variance_narrator import VarianceNarrativeOutput, narrate_variance
from app.db.base import Base
from app.models.actuals import ActualsRecord
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.simulation import RunStatus, SimulationRun
from app.models.workspace import Workspace
from app.services.actuals.variance import VarianceDelta, compute_variance
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


def _sample_delta() -> VarianceDelta:
    """A deterministic delta for narrator tests (no DB needed)."""
    return VarianceDelta(
        blueprint_id="bp_1",
        month=3,
        prior_survival_rate=0.9,
        new_survival_rate=0.4,
        survival_delta=-0.5,
        prior_runway_median=22.0,
        new_runway_median=14.0,
        runway_delta=-8.0,
        prior_resilience_score=88.0,
        new_resilience_score=50.0,
        score_delta=-38.0,
        key_changes=["revenue_engine.streams.0.churn_monthly increased from 0.05 to 0.09"],
    )


async def test_variance_delta_fields_are_numeric() -> None:
    delta = _sample_delta()
    for field in (
        "prior_survival_rate",
        "new_survival_rate",
        "survival_delta",
        "prior_runway_median",
        "new_runway_median",
        "runway_delta",
        "prior_resilience_score",
        "new_resilience_score",
        "score_delta",
    ):
        value = getattr(delta, field)
        assert isinstance(value, float), f"{field} should be float, got {type(value)}"


async def test_narrator_with_mock_provider_returns_narrative() -> None:
    """Mock provider (no API key) falls back to the deterministic narrative."""
    narrative = await narrate_variance(_sample_delta())
    assert isinstance(narrative, VarianceNarrativeOutput)
    assert narrative.headline


async def test_narrator_headline_contains_percentage() -> None:
    narrative = await narrate_variance(_sample_delta())
    assert "%" in narrative.headline
    # Headline must reference the actual prior/new survival numbers.
    assert "90%" in narrative.headline
    assert "40%" in narrative.headline
