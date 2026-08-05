"""Unit tests for the baseline simulation service (T25)."""

import json
from pathlib import Path

import pytest
from app.db.session import async_session_factory
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.workspace import Workspace
from app.schemas.simulation import SimulationStartRequest
from app.services import simulation_service as ss

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


async def _seed_blueprint() -> tuple[Workspace, BlueprintVersion]:
    payload = json.loads((FIXTURES / "blueprint_golden.json").read_text())
    async with async_session_factory() as session:
        ws = Workspace(name="T25 WS", slug="t25-ws")
        session.add(ws)
        await session.flush()
        bp = Blueprint(
            workspace_id=ws.id, name="Golden", industry="B2B SaaS", stage="Seed"
        )
        session.add(bp)
        await session.flush()
        version = BlueprintVersion(
            blueprint_id=bp.id, version=1, payload=payload
        )
        session.add(version)
        await session.commit()
        await session.refresh(version)
        return ws, version


async def test_baseline_run_persists_ticks_and_result() -> None:
    ws, version = await _seed_blueprint()
    req = SimulationStartRequest(
        blueprint_version_id=version.id, mode="baseline", seed=42
    )
    async with async_session_factory() as session:
        run = await ss.start_baseline_run(session, workspace_id=ws.id, req=req)
        assert run.status in ("completed", "dead")
        assert run.current_month == 24
        assert run.result["survived"] is True
        assert run.result["months_survived"] == 24
        assert run.result["final_cash"] > 0
        assert 0 <= run.result["resilience_score"] <= 100

        ticks = await ss.get_run_ticks(session, run.id)
        assert len(ticks) == 24
        assert [t.month for t in ticks] == list(range(1, 25))
        required = {
            "month", "cash_balance", "burn_rate", "runway_months", "revenue",
            "costs", "net_income", "mrr", "arr", "customers", "churn_rate",
            "cac", "ltv", "ltv_cac_ratio",
        }
        assert required <= set(ticks[0].kpis.keys())


async def test_same_seed_is_deterministic() -> None:
    ws, version = await _seed_blueprint()
    req = SimulationStartRequest(
        blueprint_version_id=version.id, mode="baseline", seed=42
    )
    async with async_session_factory() as session:
        run_a = await ss.start_baseline_run(session, workspace_id=ws.id, req=req)
        ticks_a = await ss.get_run_ticks(session, run_a.id)
        run_b = await ss.start_baseline_run(session, workspace_id=ws.id, req=req)
        ticks_b = await ss.get_run_ticks(session, run_b.id)
        assert [t.kpis for t in ticks_a] == [t.kpis for t in ticks_b]


async def test_generated_seed_when_omitted() -> None:
    ws, version = await _seed_blueprint()
    req = SimulationStartRequest(blueprint_version_id=version.id, mode="baseline")
    async with async_session_factory() as session:
        run = await ss.start_baseline_run(session, workspace_id=ws.id, req=req)
        assert run.seed >= 0


async def test_unknown_version_404() -> None:
    ws, _ = await _seed_blueprint()
    req = SimulationStartRequest(blueprint_version_id="bpv_nope", mode="baseline")
    async with async_session_factory() as session:
        with pytest.raises(Exception) as excinfo:
            await ss.start_baseline_run(session, workspace_id=ws.id, req=req)
        assert getattr(excinfo.value, "status_code", None) == 404


async def test_state_round_trip() -> None:
    payload = json.loads((FIXTURES / "blueprint_golden.json").read_text())
    from app.engine.state import compile_blueprint

    state = compile_blueprint(payload)
    dumped = ss.state_to_dict(state)
    restored = ss.state_from_dict(dumped)
    assert restored.month == state.month
    assert restored.financials.cash == state.financials.cash
    assert restored.streams[0].customers == state.streams[0].customers
