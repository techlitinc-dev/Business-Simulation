"""Ghost Mode service — autonomous AI-driven stress runs (T43).

Reuses T26's stress machinery: the run is created as a stress-style run with
``mode="ghost"`` and ``config={"personality": ..., "autoplay": True}``; after
each hurdle injection the GhostAgent picks an option and the decision is
applied through the same engine path as ``apply_decision``, looping to
completion or bankruptcy with zero user input.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.ghost import GhostAgent, GhostPersonality
from app.agents.llm.factory import get_llm_provider
from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.models.simulation import (
    Decision,
    RunStatus,
    SimulationEvent,
    SimulationRun,
)
from app.services import simulation_service

_PERSONALITIES: set[str] = {"aggressive", "conservative", "opportunist"}


async def start_ghost_run(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    blueprint_version_id: str,
    personality: str,
    seed: int | None,
    redis: Any = None,
) -> SimulationRun:
    """Create a ghost run and autoplay it to completion (or bankruptcy)."""
    if personality not in _PERSONALITIES:
        raise DomainError(
            status_code=422,
            detail=(
                "Invalid personality: "
                f"{personality} (expected aggressive, conservative, opportunist)"
            ),
        )

    from app.schemas.simulation import SimulationConfig, SimulationStartRequest

    req = SimulationStartRequest(
        blueprint_version_id=blueprint_version_id,
        mode="ghost",
        seed=seed,
        config=SimulationConfig(months=24),
    )
    config = req.config.model_dump(mode="json")
    config["personality"] = personality
    config["autoplay"] = True

    version = await simulation_service.get_workspace_version(
        db, workspace_id, blueprint_version_id
    )
    import random
    import secrets

    seed_value = seed if seed is not None else secrets.randbelow(2**31)
    rng = random.Random(seed_value)
    hurdle_months = simulation_service.build_hurdle_schedule(rng, req.config.months)
    config["hurdle_months"] = hurdle_months

    run = SimulationRun(
        workspace_id=workspace_id,
        blueprint_version_id=version.id,
        mode="ghost",
        status=RunStatus.RUNNING,
        seed=seed_value,
        current_month=0,
        config=config,
        started_at=None,
    )
    db.add(run)
    await db.flush()
    run.state_snapshot = simulation_service.state_to_dict(
        simulation_service.state_from_version(version)
    )
    await db.commit()
    await db.refresh(run)

    await _autoplay(db, run, redis=redis)
    return run


async def _autoplay(
    db: AsyncSession, run: SimulationRun, *, redis: Any
) -> SimulationRun:
    """Loop segments + ghost decisions until the run reaches a terminal state."""
    settings = get_settings()
    provider = get_llm_provider(settings)
    raw_personality = str(run.config.get("personality", "conservative"))
    if raw_personality in ("aggressive", "conservative", "opportunist"):
        ghost_personality: GhostPersonality = raw_personality  # type: ignore[assignment]
    else:
        ghost_personality = "conservative"

    async def _meter(response: Any) -> None:
        from app.services.metering_service import increment

        tokens = int(response.prompt_tokens) + int(response.completion_tokens)
        if tokens > 0:
            await increment(db, run.workspace_id, "llm_tokens", amount=tokens)

    ghost = GhostAgent(provider, ghost_personality, on_response=_meter)

    # Cap iterations to avoid pathological loops.
    for _ in range(60):
        run = await simulation_service.run_stress_segment(db, run, redis=redis)
        if run.status != RunStatus.AWAITING_DECISION:
            break

        event = await db.scalar(
            select(SimulationEvent)
            .where(SimulationEvent.run_id == run.id, SimulationEvent.status == "pending")
        )
        if event is None:
            break

        hurdle_payload = dict(event.payload)
        snapshot = run.state_snapshot or {}
        state = simulation_service.state_from_dict(snapshot)
        decision = await ghost.choose_option(
            hurdle_payload, simulation_service.state_to_dict(state)
        )

        await _apply_ghost_decision(db, run, event, decision, redis=redis)
        await db.refresh(run)

    if run.status not in (
        RunStatus.COMPLETED,
        RunStatus.DEAD,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
    ):
        # Force completion if the loop exhausted without a terminal state.
        run.status = RunStatus.COMPLETED
        await db.commit()
    return run


async def _apply_ghost_decision(
    db: AsyncSession,
    run: SimulationRun,
    event: SimulationEvent,
    decision: Any,
    redis: Any = None,
) -> None:
    """Mirror apply_decision's engine path, tagging the decision as ghost."""
    from app.engine.events import apply_event

    option_id = decision.option_id
    options = event.payload.get("strategic_options", [])
    chosen = next((o for o in options if o.get("option_id") == option_id), None)
    if chosen is None:
        raise DomainError(status_code=422, detail="Ghost picked unknown option")

    state = simulation_service.state_from_dict(run.state_snapshot or {})
    impact = event.payload.get("mechanical_impact", {})
    next_state = apply_event(state, impact, month=event.month)
    next_state.financials.cash += chosen.get("cash_impact_monthly", 0.0)

    projection = next(
        (p for p in event.payload.get("options_projection", []) if p.get("option_id") == option_id),
        None,
    )
    payload = {
        "actor": "ghost",
        "personality": run.config.get("personality"),
        "rationale": decision.rationale,
        "option_name": chosen.get("name"),
    }

    db.add(
        Decision(
            run_id=run.id,
            event_id=event.id,
            option_id=option_id,
            projection={**projection, **payload} if projection else payload,
        )
    )
    event.status = "resolved"
    # Assign a fresh dict — in-place JSONB mutation isn't tracked for commit.
    event.payload = {
        **event.payload,
        "chosen_option_id": option_id,
        "ghost_decision": payload,
    }
    run.state_snapshot = simulation_service.state_to_dict(next_state)
    run.current_month = event.month
    await db.commit()

    # Stream the resolved hurdle + decision to the spectator page (T43).
    if redis is not None:
        from app.services.simulation_service import publish_envelope

        await publish_envelope(redis, run.id, "event", event.payload)
        await publish_envelope(redis, run.id, "status", {"status": run.status})
