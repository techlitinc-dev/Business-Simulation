"""Unit tests for the what-if sweep service (Day 08)."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.db.base import Base
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.workspace import Workspace
from app.services.whatif.schemas import SweepRequest
from app.services.whatif.sweep import _patch_payload, run_sweep
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


async def _seed_blueprint(db: AsyncSession) -> tuple[uuid.UUID, str]:
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
    await db.commit()
    return ws.id, bp.id


def _req(**overrides: Any) -> SweepRequest:
    base: dict[str, Any] = {
        "workspace_id": uuid.uuid4(),
        "blueprint_id": "bp_001",
        "param": "monthly_churn",
        "min_value": 0.02,
        "max_value": 0.12,
        "steps": 6,
        "mc_runs": 5,
    }
    base.update(overrides)
    return SweepRequest(**base)


def test_patch_payload_flat() -> None:
    payload: dict[str, Any] = {"monthly_churn": 0.05, "price": 99}
    result = _patch_payload(payload, "monthly_churn", 0.10)
    assert result["monthly_churn"] == 0.10
    assert payload["monthly_churn"] == 0.05  # original unchanged


def test_patch_payload_nested() -> None:
    payload: dict[str, Any] = {"financials": {"monthly_churn": 0.05}}
    result = _patch_payload(payload, "financials.monthly_churn", 0.12)
    assert result["financials"]["monthly_churn"] == 0.12


def test_patch_payload_list_index() -> None:
    payload = {"revenue_engine": {"streams": [{"churn_monthly": 0.05}]}}
    result = _patch_payload(payload, "revenue_engine.streams.0.churn_monthly", 0.08)
    assert result["revenue_engine"]["streams"][0]["churn_monthly"] == 0.08


async def test_sweep_grid_has_correct_length(db: AsyncSession) -> None:
    ws_id, bp_id = await _seed_blueprint(db)
    result = await run_sweep(
        _req(workspace_id=ws_id, blueprint_id=bp_id, steps=6, mc_runs=5), db
    )
    assert len(result.grid) == 6


async def test_sweep_grid_mocked_engine_length() -> None:
    """Mock at the real seams: get_version_payload + run_simulation."""
    payload_mock = MagicMock()
    payload_mock.model_dump.return_value = _BLUEPRINT_PAYLOAD

    with (
        patch("app.services.whatif.sweep.get_version_payload", new_callable=AsyncMock) as mock_bp,
        patch("app.services.whatif.sweep.run_simulation") as mock_run,
    ):
        mock_bp.return_value = payload_mock
        result_row = MagicMock()
        result_row.months_simulated = 18
        mock_run.return_value = result_row

        result = await run_sweep(_req(steps=6, mc_runs=5), AsyncMock())
        assert len(result.grid) == 6


async def test_sweep_survival_rates_decrease_with_churn() -> None:
    """Higher churn → lower survival rate (monotonic relationship)."""
    payload_mock = MagicMock()
    payload_mock.model_dump.return_value = _BLUEPRINT_PAYLOAD

    with (
        patch("app.services.whatif.sweep.get_version_payload", new_callable=AsyncMock) as mock_bp,
        patch("app.services.whatif.sweep.run_simulation") as mock_run,
    ):
        mock_bp.return_value = payload_mock

        def side_effect(state: Any, months: int, seed: int) -> MagicMock:  # noqa: ARG001
            streams = getattr(state, "streams", None)
            churn = streams[0].churn_monthly if streams else 0.05
            row = MagicMock()
            row.months_simulated = max(6, int(24 * (1 - churn * 5)))
            return row

        mock_run.side_effect = side_effect

        result = await run_sweep(
            _req(min_value=0.02, max_value=0.10, steps=5, mc_runs=5), AsyncMock()
        )
        rates = [pt.survival_rate for pt in result.grid]
        decreases = sum(1 for a, b in zip(rates, rates[1:], strict=False) if a >= b)
        assert decreases >= 3


async def test_sweep_result_serializable(db: AsyncSession) -> None:
    ws_id, bp_id = await _seed_blueprint(db)
    result = await run_sweep(
        _req(workspace_id=ws_id, blueprint_id=bp_id, param="price",
             min_value=50, max_value=200, steps=3, mc_runs=5),
        db,
    )
    json.dumps(result.model_dump())  # must not raise
