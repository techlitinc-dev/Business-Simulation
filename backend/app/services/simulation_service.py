"""Simulation run business logic: baseline runs, stress segments, control.

The engine stays pure — every DB/Redis/LLM I/O lives here (or in the Monte
Carlo worker). ``kpi_snapshot`` from ``app.engine.metrics`` is the canonical
per-month KPI shape stored in ``TickLog.kpis`` and streamed over WebSocket.
"""

from __future__ import annotations

import json
import random
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.engine.loop import tick
from app.engine.metrics import kpi_snapshot, resilience_score
from app.engine.state import BusinessState, compile_blueprint
from app.models.blueprint import BlueprintVersion
from app.models.simulation import (
    TERMINAL_STATUSES,
    Decision,
    RunStatus,
    SimulationEvent,
    SimulationRun,
    TickLog,
)
from app.schemas.simulation import (
    SimulationRunResponse,
    SimulationStartRequest,
    TickLogResponse,
)

logger = structlog.get_logger("forge.simulations")

#: Redis keys / pub-sub channel for live run output (TTL 3600s).
PROGRESS_KEY = "sim:{run_id}:progress"
CONTROL_KEY = "sim:{run_id}:control"
STREAM_CHANNEL = "sim:{run_id}:stream"


def build_baseline_result(
    state: BusinessState, tick_logs: list[Any], months_survived: int
) -> dict[str, Any]:
    """Compact outcome summary persisted on ``SimulationRun.result`` (T25)."""
    cashes = [float(t.kpis["cash_balance"]) for t in tick_logs]
    burn = state.financials.monthly_burn
    runway = state.financials.cash / burn if burn > 0 else float("inf")
    return {
        "survived": not state.bankrupt,
        "months_survived": months_survived,
        "final_cash": round(float(state.financials.cash), 2),
        "final_mrr": round(float(state.financials.mrr), 2),
        "peak_cash": round(max(cashes), 2) if cashes else 0.0,
        "min_cash": round(min(cashes), 2) if cashes else 0.0,
        "runway_months": round(runway, 1) if runway != float("inf") else 0.0,
        "resilience_score": resilience_score(state, months_survived, len(tick_logs)),
    }


def _random_seed(rng: Any) -> int:
    """A seeded 31-bit draw from an rng (or secrets when rng is None)."""
    if rng is None:
        return int(secrets.randbelow(2**31))
    return int(rng.randrange(0, 2**31))


def build_hurdle_schedule(rng: Any, months: int) -> list[int]:
    """Deterministic hurdle months per seed: first at randint(4,8), then every
    randint(3,6) months."""
    if months < 4:
        return []
    schedule: list[int] = []
    month = rng.randint(4, min(8, months))
    while month <= months:
        schedule.append(month)
        month += rng.randint(3, 6)
    return schedule


def _run_trace(
    state: BusinessState,
    months: int,
    seed: int,
    *,
    offset: int = 0,
) -> tuple[BusinessState, list[Any]]:
    """Step the engine month by month, emitting shared-shape KPI tick rows.

    ``offset`` shifts the tick months to their absolute position in the full
    run (used by stress segments that resume from a parked state).
    """
    from app.engine.loop import _customer_movement

    rng = random.Random(seed)
    sim = state.snapshot()
    logs: list[Any] = []
    for _ in range(months):
        prev = sim
        sim = tick(sim, rng)
        new_customers, churned = _customer_movement(prev, sim)
        kpis = kpi_snapshot(sim, new_customers, churned)
        kpis["month"] = float(sim.month + offset)
        logs.append(TickLog(month=sim.month + offset, kpis=kpis))
        if sim.bankrupt:
            break
    return sim, logs


async def get_workspace_version(
    db: AsyncSession, workspace_id: uuid.UUID, blueprint_version_id: str
) -> BlueprintVersion:
    """Load a blueprint version scoped to the workspace; 404 on any miss."""
    from app.models.blueprint import Blueprint

    version = await db.scalar(
        select(BlueprintVersion)
        .join(BlueprintVersion.blueprint)
        .where(
            BlueprintVersion.id == blueprint_version_id,
            Blueprint.workspace_id == workspace_id,
        )
    )
    if version is None:
        raise DomainError(status_code=404, detail="Blueprint version not found")
    return version


def state_from_version(version: BlueprintVersion) -> BusinessState:
    """Compile a blueprint version payload to engine state."""
    return compile_blueprint(dict(version.payload))


async def get_workspace_run(
    db: AsyncSession, workspace_id: uuid.UUID, run_id: str
) -> SimulationRun:
    """Load a run scoped to the workspace; 404 on any miss."""
    run = await db.scalar(
        select(SimulationRun).where(
            SimulationRun.id == run_id,
            SimulationRun.workspace_id == workspace_id,
        )
    )
    if run is None:
        raise DomainError(status_code=404, detail="Simulation run not found")
    return run


async def _persist_ticks(
    db: AsyncSession, run: SimulationRun, tick_logs: list[Any]
) -> None:
    """Insert engine tick logs for a run, skipping months already recorded."""
    existing = {
        (month,) for month in (await db.scalars(
            select(TickLog.month).where(TickLog.run_id == run.id)
        ))
    }
    for log in tick_logs:
        if (log.month,) in existing:
            continue
        db.add(
            TickLog(
                run_id=run.id,
                month=log.month,
                kpis=log.kpis,
            )
        )


def _run_response(
    run: SimulationRun, progress: dict[str, Any] | None = None
) -> SimulationRunResponse:
    return SimulationRunResponse.model_validate(run).model_copy(
        update={"progress": progress}
    )


async def start_baseline_run(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    req: SimulationStartRequest,
) -> SimulationRun:
    """Run a full baseline simulation synchronously (24 months <100ms)."""
    version = await get_workspace_version(db, workspace_id, req.blueprint_version_id)
    seed = req.seed if req.seed is not None else secrets.randbelow(2**31)
    months = req.config.months

    state = state_from_version(version)
    final_state, tick_rows = _run_trace(state, months, seed=seed)

    run = SimulationRun(
        workspace_id=workspace_id,
        blueprint_version_id=version.id,
        mode="baseline",
        status=RunStatus.COMPLETED if not final_state.bankrupt else RunStatus.DEAD,
        seed=seed,
        current_month=final_state.month,
        config=req.config.model_dump(mode="json"),
        result=build_baseline_result(final_state, tick_rows, final_state.month),
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
    )
    db.add(run)
    await db.flush()

    for row in tick_rows:
        row.run_id = run.id
        db.add(row)
    await db.commit()
    await db.refresh(run)
    return run


async def get_run_ticks(db: AsyncSession, run_id: str) -> list[TickLogResponse]:
    rows = await db.scalars(
        select(TickLog).where(TickLog.run_id == run_id).order_by(TickLog.month)
    )
    return [TickLogResponse.model_validate(r) for r in rows]


async def get_run_progress(redis: Any, run_id: str) -> dict[str, Any] | None:
    """Best-effort read of the Monte Carlo progress key (None without Redis)."""
    try:
        raw = await redis.get(PROGRESS_KEY.format(run_id=run_id))
    except Exception:  # noqa: BLE001 - best-effort per shared contract
        return None
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return dict(parsed) if isinstance(parsed, dict) else None
    except (TypeError, ValueError):
        return None


async def publish_envelope(redis: Any, run_id: str, type_: str, data: Any) -> None:
    """Publish a WS envelope to ``sim:{run_id}:stream`` — best-effort."""
    if redis is None:
        return
    message = json.dumps({"type": type_, "data": data})
    try:
        await redis.publish(STREAM_CHANNEL.format(run_id=run_id), message)
    except Exception:  # noqa: BLE001 - never break a run without Redis
        logger.debug("publish_envelope failed (redis unavailable)", run_id=run_id)


async def publish_status(
    redis: Any, run: SimulationRun, status: str | None = None
) -> None:
    await publish_envelope(redis, run.id, "status", {"status": status or run.status})


def state_to_dict(state: BusinessState) -> dict[str, Any]:
    """Serialize engine state so it can be parked in ``run.state_snapshot`` (T26)."""
    from dataclasses import asdict

    return asdict(state)


def state_from_dict(data: dict[str, Any]) -> BusinessState:
    """Deserialize a parked engine state; missing snapshot means compile fresh."""
    return _state_from_dict(data)


def _state_from_dict(data: dict[str, Any]) -> BusinessState:
    """Manual deserialization of the engine state dataclass tree."""
    from app.engine.state import (
        BusinessState,
        FinancialState,
        MarketState,
        RevenueStream,
        TeamMember,
        TriggerEvent,
    )

    fin = data["financials"]
    financials = FinancialState(
        cash=float(fin["cash"]),
        mrr=float(fin["mrr"]),
        arr=float(fin["arr"]),
        monthly_burn=float(fin["monthly_burn"]),
        fixed_monthly=float(fin["fixed_monthly"]),
        variable_per_unit=float(fin["variable_per_unit"]),
        ar_days=int(fin["ar_days"]),
        ap_days=int(fin["ap_days"]),
        gross_margin=float(fin["gross_margin"]),
        team=[
            TeamMember(r["role"], float(r["salary_annual"]), int(r["hire_month"]))
            for r in fin["team"]
        ],
        accounts_receivable=float(fin.get("accounts_receivable", 0.0)),
        accounts_payable=float(fin.get("accounts_payable", 0.0)),
        profitable_streak=int(fin.get("profitable_streak", 0)),
    )
    market = MarketState(
        market_size=int(data["market"]["market_size"]),
        market_share=float(data["market"]["market_share"]),
        base_demand=float(data["market"]["base_demand"]),
        price=float(data["market"]["price"]),
        reference_price=float(data["market"]["reference_price"]),
        price_elasticity=float(data["market"]["price_elasticity"]),
        seasonality=[float(x) for x in data["market"]["seasonality"]],
        competitor_pressure=float(data["market"]["competitor_pressure"]),
        brand_sentiment=float(data["market"].get("brand_sentiment", 0.5)),
    )
    streams = [
        RevenueStream(
            name=s["name"],
            pricing_model=s["pricing_model"],
            price_point=float(s["price_point"]),
            projected_customers_month_12=int(s["projected_customers_month_12"]),
            ltv=float(s["ltv"]),
            cac=float(s["cac"]),
            churn_monthly=float(s["churn_monthly"]),
            customers=int(s.get("customers", 0)),
        )
        for s in data["streams"]
    ]
    triggers = [
        TriggerEvent(t["month"], t["trigger"], t["detail"])
        for t in data.get("triggers_fired", [])
    ]
    return BusinessState(
        month=int(data["month"]),
        financials=financials,
        market=market,
        streams=streams,
        triggers_fired=triggers,
        active_event_effects=list(data.get("active_event_effects", [])),
        bankrupt=bool(data.get("bankrupt", False)),
    )


async def advance_ticks_and_publish(
    db: AsyncSession,
    run: SimulationRun,
    state: BusinessState,
    prev_state: BusinessState | None,
    redis: Any,
) -> list[Any]:
    """Persist engine tick rows for a newly-advanced state, publishing each."""
    persisted: list[Any] = []
    for month in range(prev_state.month + 1 if prev_state else 1, state.month + 1):
        # Reconstruct KPI shape for months that fall between parked segments
        # (the engine only hands us the final state + its own tick logs).
        kpis = kpi_snapshot(state, 0, 0)
        kpis["month"] = float(month)
        db.add(TickLog(run_id=run.id, month=month, kpis=kpis))
        persisted.append({"month": month, "kpis": kpis})
        await publish_envelope(redis, run.id, "tick", {"month": month, "kpis": kpis})
    return persisted


# ---------------------------------------------------------------------------
# T26 — stress-test mode
# ---------------------------------------------------------------------------


def _difficulty_value(difficulty: str) -> int:
    return {"standard": 1, "hard": 4, "nightmare": 10}.get(difficulty, 1)


def _next_hurdle_month(config: dict[str, Any], current_month: int) -> int | None:
    for month in config.get("hurdle_months", []):
        if month > current_month:
            return int(month)
    return None


async def start_stress_run(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    req: SimulationStartRequest,
    redis: Any,
) -> SimulationRun:
    """Create a stress run and run its first segment synchronously.

    Deterministic per seed: hurdle months are sampled once with
    ``random.Random(seed)`` and stored in ``run.config["hurdle_months"]``.
    """
    version = await get_workspace_version(db, workspace_id, req.blueprint_version_id)
    seed = req.seed if req.seed is not None else secrets.randbelow(2**31)
    months = req.config.months

    rng = random.Random(seed)
    hurdle_months = build_hurdle_schedule(rng, months)
    config = req.config.model_dump(mode="json")
    config["hurdle_months"] = hurdle_months

    run = SimulationRun(
        workspace_id=workspace_id,
        blueprint_version_id=version.id,
        mode="stress",
        status=RunStatus.RUNNING,
        seed=seed,
        current_month=0,
        config=config,
        started_at=datetime.now(UTC),
    )
    db.add(run)
    await db.flush()
    run.state_snapshot = state_to_dict(state_from_version(version))
    await db.commit()
    await db.refresh(run)

    await run_stress_segment(db, run, redis=redis)
    return run


async def run_stress_segment(
    db: AsyncSession, run: SimulationRun, *, redis: Any
) -> SimulationRun:
    """Advance a stress run to its next hurdle, the end, or bankruptcy."""
    from app.agents.chronicle import Chronicle
    from app.agents.hurdle_generator import HurdleGenerator
    from app.agents.llm.factory import get_llm_provider
    from app.agents.strategist import Strategist

    settings = get_settings()
    provider = get_llm_provider(settings)

    # T41: meter LLM tokens for every agent call this segment makes.
    async def _meter_tokens(response: Any) -> None:
        from app.services.metering_service import increment

        tokens = int(response.prompt_tokens) + int(response.completion_tokens)
        if tokens > 0:
            await increment(db, run.workspace_id, "llm_tokens", amount=tokens)

    months = int(run.config.get("months", 24))
    current_month = run.current_month
    next_hurdle = _next_hurdle_month(run.config, current_month)

    # Resume from parked state or compile fresh.
    if run.state_snapshot:
        state = state_from_dict(run.state_snapshot)
    else:
        version = await get_workspace_version(
            db, uuid.UUID(str(run.workspace_id)), run.blueprint_version_id
        )
        state = state_from_version(version)

    # Advance the loop in one synchronous stretch: to the month BEFORE the next
    # hurdle, the run end, or bankruptcy.
    target = (next_hurdle - 1) if next_hurdle is not None else months
    if target > current_month:
        state, tick_rows = _run_trace(
            state, target - state.month, seed=run.seed, offset=0
        )
        for row in tick_rows:
            row.run_id = run.id
            db.add(row)
        await db.commit()

    if state.bankrupt:
        run.status = RunStatus.DEAD
        run.current_month = state.month
        run.result = build_baseline_result(
            state, await get_run_ticks(db, run.id), state.month
        )
        run.finished_at = datetime.now(UTC)
        await db.commit()
        await publish_status(redis, run)
        return run

    if next_hurdle is None:
        run.status = RunStatus.COMPLETED
        run.current_month = months
        run.result = build_baseline_result(
            state, await get_run_ticks(db, run.id), months
        )
        run.finished_at = datetime.now(UTC)
        run.state_snapshot = None
        await db.commit()
        await publish_status(redis, run)
        return run

    # We are AT a hurdle month. Build the vital-signs snapshot from the latest
    # persisted KPI row (state is current as of the month before the hurdle).
    hurdle_month = next_hurdle
    kpis = await _latest_kpis(db, run.id, state)

    chronicle = Chronicle()
    if run.config.get("chronicle"):
        chronicle = Chronicle.from_dict(run.config["chronicle"])

    difficulty = _difficulty_value(run.config.get("difficulty", "standard"))
    generator = HurdleGenerator(provider, on_response=_meter_tokens)
    hurdle = await generator.generate(
        state, kpis, chronicle, difficulty=difficulty, month=hurdle_month
    )

    # Strategist: attach a 12-month engine projection per option.
    strategist = Strategist(provider, on_response=_meter_tokens)
    advise = await strategist.advise(state, kpis, hurdle, chronicle)
    payload = hurdle.model_dump(mode="json")
    payload["options_projection"] = [
        p.model_dump(mode="json") for p in advise.projections
    ]
    payload["strategic_options"] = [
        o.model_dump(mode="json") for o in advise.options
    ]

    event = SimulationEvent(
        run_id=run.id,
        month=hurdle_month,
        payload=payload,
        status="pending",
    )
    db.add(event)

    # Park state + chronicle, then wait for the user's decision.
    run.state_snapshot = state_to_dict(state)
    run.config["chronicle"] = chronicle.to_dict()
    run.current_month = hurdle_month
    run.status = RunStatus.AWAITING_DECISION
    await db.commit()
    await db.refresh(event)

    # The LLM generates its own event_id; normalize it to the DB row id so the
    # frontend sends back an id the decide endpoint can resolve (T26). Assign a
    # fresh dict — in-place mutation after refresh() isn't tracked by SQLAlchemy
    # for plain JSONB columns.
    if event.payload.get("event_id") != event.id:
        event.payload = {**event.payload, "event_id": event.id}
        await db.commit()

    await publish_envelope(redis, run.id, "event", event.payload)
    await publish_status(redis, run)
    return run


async def _latest_kpis(db: AsyncSession, run_id: str, state: BusinessState) -> dict[str, Any]:
    row = await db.scalar(
        select(TickLog).where(TickLog.run_id == run_id).order_by(TickLog.month.desc())
    )
    if row is not None:
        return row.kpis
    return kpi_snapshot(state, 0, 0)


async def apply_decision(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    run_id: str,
    event_id: str,
    option_id: str,
    redis: Any,
) -> tuple[SimulationRun, Decision]:
    """Apply a user decision to a pending hurdle and resume the run (T26)."""
    from app.engine.events import apply_event

    run = await get_workspace_run(db, workspace_id, run_id)
    if run.status != RunStatus.AWAITING_DECISION:
        raise DomainError(status_code=409, detail="Run is not awaiting a decision")
    event = await db.scalar(
        select(SimulationEvent).where(
            SimulationEvent.run_id == run.id,
            SimulationEvent.id == event_id,
        )
    )
    if event is None or event.status != "pending":
        raise DomainError(status_code=409, detail="Event is not pending")

    options = event.payload.get("strategic_options", [])
    chosen = next((o for o in options if o.get("option_id") == option_id), None)
    if chosen is None:
        raise DomainError(status_code=422, detail="Unknown option_id")

    state = state_from_dict(run.state_snapshot) if run.state_snapshot else None
    if state is None:
        version = await get_workspace_version(
            db, uuid.UUID(str(run.workspace_id)), run.blueprint_version_id
        )
        state = state_from_version(version)

    # Apply the hurdle's mechanical impact + the chosen option's monthly cash impact.
    impact = event.payload.get("mechanical_impact", {})
    next_state = apply_event(state, impact, month=event.month)
    next_state.financials.cash += chosen.get("cash_impact_monthly", 0.0)

    projection = next(
        (p for p in event.payload.get("options_projection", []) if p.get("option_id") == option_id),
        None,
    )

    decision = Decision(
        run_id=run.id,
        event_id=event.id,
        option_id=option_id,
        projection=projection,
    )
    db.add(decision)
    event.status = "resolved"
    event.payload["chosen_option_id"] = option_id
    run.state_snapshot = state_to_dict(next_state)
    run.current_month = event.month
    await db.commit()
    await db.refresh(decision)

    await publish_status(redis, run)
    await run_stress_segment(db, run, redis=redis)
    return run, decision


# ---------------------------------------------------------------------------
# T27 — Monte Carlo dispatch
# ---------------------------------------------------------------------------


async def start_monte_carlo_run(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    req: SimulationStartRequest,
    redis: Any,
) -> SimulationRun:
    """Create a pending Monte Carlo run and enqueue the Celery batch task."""
    from app.workers.monte_carlo import run_monte_carlo

    version = await get_workspace_version(db, workspace_id, req.blueprint_version_id)
    seed = req.seed if req.seed is not None else secrets.randbelow(2**31)
    config = req.config.model_dump(mode="json")

    run = SimulationRun(
        workspace_id=workspace_id,
        blueprint_version_id=version.id,
        mode="monte_carlo",
        status=RunStatus.PENDING,
        seed=seed,
        current_month=0,
        config=config,
        started_at=datetime.now(UTC),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    try:
        run_monte_carlo.delay(run.id)
    except Exception:  # noqa: BLE001 - Redis broker down in dev/tests
        logger.warning("monte carlo enqueue failed", run_id=run.id, exc_info=True)
        run.status = RunStatus.FAILED
        run.result = {"error": "Failed to enqueue Monte Carlo batch"}
        run.finished_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(run)
    return run


async def start_simulation(
    db: AsyncSession, *, workspace_id: uuid.UUID, req: SimulationStartRequest, redis: Any = None
) -> SimulationRun:
    """Dispatch a run to the right mode handler."""
    if req.mode == "baseline":
        return await start_baseline_run(db, workspace_id=workspace_id, req=req)
    if req.mode == "stress":
        return await start_stress_run(db, workspace_id=workspace_id, req=req, redis=redis)
    if req.mode == "monte_carlo":
        return await start_monte_carlo_run(db, workspace_id=workspace_id, req=req, redis=redis)
    if req.mode == "ghost":
        from app.services.ghost_service import start_ghost_run

        personality = req.config.personality
        if personality is None:
            raise DomainError(
                status_code=422,
                detail="config.personality is required for ghost mode",
            )
        return await start_ghost_run(
            db,
            workspace_id=workspace_id,
            blueprint_version_id=req.blueprint_version_id,
            personality=personality,
            seed=req.seed,
            redis=redis,
        )
    raise DomainError(status_code=422, detail=f"Unknown mode: {req.mode}")


# ---------------------------------------------------------------------------
# T28 — run controls
# ---------------------------------------------------------------------------


async def control_run(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    run_id: str,
    action: str,
    redis: Any,
) -> SimulationRun:
    """Pause / resume / cancel a run (else 409)."""
    run = await get_workspace_run(db, workspace_id, run_id)
    if run.status in TERMINAL_STATUSES:
        raise DomainError(status_code=409, detail=f"Cannot {action} a terminal run")

    if action == "pause":
        if run.status not in (RunStatus.RUNNING, RunStatus.AWAITING_DECISION):
            raise DomainError(status_code=409, detail="Run is not running")
        run.status = RunStatus.PAUSED
    elif action == "resume":
        if run.status != RunStatus.PAUSED:
            raise DomainError(status_code=409, detail="Run is not paused")
        pending = await db.scalar(
            select(SimulationEvent).where(
                SimulationEvent.run_id == run.id,
                SimulationEvent.status == "pending",
            )
        )
        run.status = (
            RunStatus.AWAITING_DECISION if pending is not None else RunStatus.RUNNING
        )
    elif action == "cancel":
        run.status = RunStatus.CANCELLED
        run.finished_at = datetime.now(UTC)
    else:
        raise DomainError(status_code=422, detail=f"Unknown action: {action}")

    await db.commit()
    await db.refresh(run)
    await publish_status(redis, run)
    return run
