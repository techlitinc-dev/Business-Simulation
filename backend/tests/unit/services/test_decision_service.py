"""Unit tests for stress mode + decision application (T26)."""

import json
from pathlib import Path

import pytest
from app.db.session import async_session_factory
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.simulation import Decision, SimulationEvent
from app.models.workspace import Workspace
from app.schemas.hurdle import HurdleEvent
from app.schemas.simulation import SimulationStartRequest
from app.services.simulation_service import apply_decision, start_stress_run
from sqlalchemy import select

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


async def _seed_blueprint() -> tuple[Workspace, BlueprintVersion]:
    payload = json.loads((FIXTURES / "blueprint_golden.json").read_text())
    async with async_session_factory() as session:
        ws = Workspace(name="T26 WS", slug="t26-ws")
        session.add(ws)
        await session.flush()
        bp = Blueprint(
            workspace_id=ws.id, name="Golden", industry="B2B SaaS", stage="Seed"
        )
        session.add(bp)
        await session.flush()
        version = BlueprintVersion(blueprint_id=bp.id, version=1, payload=payload)
        session.add(version)
        await session.commit()
        await session.refresh(version)
        return ws, version


async def test_stress_run_reaches_awaiting_decision() -> None:
    ws, version = await _seed_blueprint()
    req = SimulationStartRequest(
        blueprint_version_id=version.id, mode="stress", seed=42
    )
    async with async_session_factory() as session:
        run = await start_stress_run(session, workspace_id=ws.id, req=req, redis=None)
        assert run.status == "awaiting_decision"
        assert run.current_month in (4, 5, 6, 7, 8)

        event = (
            await session.scalars(
                select(SimulationEvent).where(SimulationEvent.run_id == run.id)
            )
        ).first()
        assert event is not None
        assert event.status == "pending"
        # The base Format B fields must validate; options/projection are merged
        # on top by the strategist, so strip them before schema validation.
        base = {
            k: v
            for k, v in event.payload.items()
            if k not in ("strategic_options", "options_projection")
        }
        hurdle = HurdleEvent.model_validate(base)
        assert hurdle.category in (
            "market", "operational", "financial", "black_swan", "internal"
        )
        assert 2 <= len(event.payload["strategic_options"]) <= 4
        assert len(event.payload["options_projection"]) == len(
            event.payload["strategic_options"]
        )


async def test_same_seed_identical_stress_runs() -> None:
    ws, version = await _seed_blueprint()
    req = SimulationStartRequest(
        blueprint_version_id=version.id, mode="stress", seed=7
    )
    async with async_session_factory() as session:
        run_a = await start_stress_run(session, workspace_id=ws.id, req=req, redis=None)
        evt_a = (
            await session.scalars(
                select(SimulationEvent).where(SimulationEvent.run_id == run_a.id)
            )
        ).first()
        run_b = await start_stress_run(session, workspace_id=ws.id, req=req, redis=None)
        evt_b = (
            await session.scalars(
                select(SimulationEvent).where(SimulationEvent.run_id == run_b.id)
            )
        ).first()
        assert run_a.config["hurdle_months"] == run_b.config["hurdle_months"]
        assert evt_a.payload == evt_b.payload


async def test_apply_decision_advances_and_resolves() -> None:
    ws, version = await _seed_blueprint()
    req = SimulationStartRequest(
        blueprint_version_id=version.id, mode="stress", seed=42
    )
    async with async_session_factory() as session:
        run = await start_stress_run(session, workspace_id=ws.id, req=req, redis=None)
        event = (
            await session.scalars(
                select(SimulationEvent).where(SimulationEvent.run_id == run.id)
            )
        ).first()
        option_id = event.payload["strategic_options"][0]["option_id"]

        run, decision = await apply_decision(
            session,
            workspace_id=ws.id,
            run_id=run.id,
            event_id=event.id,
            option_id=option_id,
            redis=None,
        )
        assert decision.option_id == option_id
        assert run.status in ("awaiting_decision", "completed", "dead")
        assert run.current_month > event.month

        event_after = await session.get(SimulationEvent, event.id)
        assert event_after.status == "resolved"
        assert event_after.payload["chosen_option_id"] == option_id

        decisions = (
            await session.scalars(
                select(Decision).where(Decision.run_id == run.id)
            )
        ).all()
        assert len(decisions) == 1


async def test_apply_decision_wrong_state_409() -> None:
    ws, version = await _seed_blueprint()
    req = SimulationStartRequest(
        blueprint_version_id=version.id, mode="stress", seed=42
    )
    async with async_session_factory() as session:
        run = await start_stress_run(session, workspace_id=ws.id, req=req, redis=None)
        event = (
            await session.scalars(
                select(SimulationEvent).where(SimulationEvent.run_id == run.id)
            )
        ).first()
        option_id = event.payload["strategic_options"][0]["option_id"]

        # Resolve once.
        await apply_decision(
            session,
            workspace_id=ws.id,
            run_id=run.id,
            event_id=event.id,
            option_id=option_id,
            redis=None,
        )
        # Second decision on the same (now resolved) event -> 409.
        with pytest.raises(Exception) as excinfo:
            await apply_decision(
                session,
                workspace_id=ws.id,
                run_id=run.id,
                event_id=event.id,
                option_id=option_id,
                redis=None,
            )
        assert getattr(excinfo.value, "status_code", None) == 409


async def test_apply_decision_unknown_option_422() -> None:
    ws, version = await _seed_blueprint()
    req = SimulationStartRequest(
        blueprint_version_id=version.id, mode="stress", seed=42
    )
    async with async_session_factory() as session:
        run = await start_stress_run(session, workspace_id=ws.id, req=req, redis=None)
        event = (
            await session.scalars(
                select(SimulationEvent).where(SimulationEvent.run_id == run.id)
            )
        ).first()
        with pytest.raises(Exception) as excinfo:
            await apply_decision(
                session,
                workspace_id=ws.id,
                run_id=run.id,
                event_id=event.id,
                option_id="Z",
                redis=None,
            )
        assert getattr(excinfo.value, "status_code", None) == 422


async def test_decision_impact_visible_in_ticks() -> None:
    ws, version = await _seed_blueprint()
    req = SimulationStartRequest(
        blueprint_version_id=version.id, mode="stress", seed=42
    )
    async with async_session_factory() as session:
        run = await start_stress_run(session, workspace_id=ws.id, req=req, redis=None)
        event = (
            await session.scalars(
                select(SimulationEvent).where(SimulationEvent.run_id == run.id)
            )
        ).first()
        # Pick the option with a non-zero monthly cash impact.
        options = event.payload["strategic_options"]
        option = next(o for o in options if o.get("cash_impact_monthly") != 0)
        cash_before = run.state_snapshot["financials"]["cash"]

        run, _ = await apply_decision(
            session,
            workspace_id=ws.id,
            run_id=run.id,
            event_id=event.id,
            option_id=option["option_id"],
            redis=None,
        )
        cash_after = run.state_snapshot["financials"]["cash"]
        # The hurdle's one-time deltas plus the option's monthly impact moved cash.
        assert cash_after != cash_before
