"""Monte Carlo worker — deterministic batch simulation runs (T27).

Deliberately LLM-free in the hot loop (spec §14): hurdles are sampled from a
deterministic in-process template pool keyed by category, and decisions are
auto-applied with a fixed policy (highest success probability, then lowest
option id). Progress is written to Redis (best-effort) after every sub-run and
the task aborts when the control flag is set to ``cancel``.
"""

from __future__ import annotations

import asyncio
import json
import random
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from statistics import median
from typing import Any

import structlog
from redis.asyncio import Redis

from app.core.config import get_settings
from app.engine.events import apply_event
from app.engine.loop import tick
from app.engine.state import compile_blueprint
from app.models.simulation import RunStatus, SimulationRun
from app.schemas.simulation import MonteCarloResult, MonteCarloRunSummary
from app.workers.celery_app import celery_app

logger = structlog.get_logger("forge.monte_carlo")

#: Deterministic hurdle template pool — 5 spec §6 categories × 2 templates.
HURDLE_TEMPLATES: list[dict[str, Any]] = [
    {
        "category": "market",
        "name": "Competitor undercut",
        "immediate": {"cac_delta_percent": 30, "churn_delta_percent": 10},
    },
    {
        "category": "market",
        "name": "Market downturn",
        "immediate": {"new_signups_delta_percent": -35},
    },
    {
        "category": "operational",
        "name": "Key hire leaves",
        "immediate": {"cash_burn_delta_monthly": 8000, "team_morale_delta": -0.2},
    },
    {
        "category": "operational",
        "name": "Vendor cost spike",
        "immediate": {"cash_burn_delta_monthly": 12000},
    },
    {
        "category": "financial",
        "name": "Payment cycle lengthens",
        "immediate": {"cash_delta_one_time": -50000},
    },
    {
        "category": "financial",
        "name": "Investor pulls term sheet",
        "immediate": {"cash_delta_one_time": -75000, "cac_delta_percent": 15},
    },
    {
        "category": "black_swan",
        "name": "Regulatory whiplash",
        "immediate": {"new_signups_delta_percent": -50, "cac_delta_percent": 25},
    },
    {
        "category": "black_swan",
        "name": "Platform outage",
        "immediate": {"churn_delta_percent": 20, "cash_burn_delta_monthly": 5000},
    },
    {
        "category": "internal",
        "name": "Founder burnout",
        "immediate": {"team_morale_delta": -0.3, "cash_burn_delta_monthly": 6000},
    },
    {
        "category": "internal",
        "name": "Quality crisis",
        "immediate": {"churn_delta_percent": 15, "cac_delta_percent": 20},
    },
]

#: Two generic options attached to every template hurdle.
_GENERIC_OPTIONS: list[dict[str, Any]] = [
    {
        "option_id": "A",
        "name": "Cut costs",
        "description": "Reduce spend to extend runway.",
        "cash_impact_monthly": -8000,
        "probability_success": 0.7,
        "second_order_risk": "Growth stalls.",
        "required_execution": "Trim discretionary spend.",
    },
    {
        "option_id": "B",
        "name": "Push growth",
        "description": "Spend more to win the market.",
        "cash_impact_monthly": -15000,
        "probability_success": 0.5,
        "second_order_risk": "Cash runway shortens.",
        "required_execution": "Launch aggressive campaign.",
    },
]


def _control_key(run_id: str) -> str:
    return f"sim:{run_id}:control"


def _progress_key(run_id: str) -> str:
    return f"sim:{run_id}:progress"


def _channel(run_id: str) -> str:
    return f"sim:{run_id}:stream"


def _auto_option(options: list[dict[str, Any]]) -> dict[str, Any]:
    """Fixed policy: highest probability_success, tie-break by lowest option_id."""
    return max(
        options,
        key=lambda o: (
            o.get("probability_success", 0.0),
            -len(o.get("option_id", "")),
        ),
    )


def _hurdle_months(rng: random.Random, months: int) -> list[int]:
    """Same schedule as T26: first at randint(4,8), then every randint(3,6)."""
    if months < 4:
        return []
    schedule: list[int] = []
    month = rng.randint(4, min(8, months))
    while month <= months:
        schedule.append(month)
        month += rng.randint(3, 6)
    return schedule


def run_one(
    blueprint_payload: dict[str, Any],
    seed: int,
    months: int,
) -> dict[str, Any]:
    """Run one seeded sub-simulation with template hurdles and auto-decisions.

    Returns ``{seed, survived, lifespan_months, kill_vector}`` where
    ``kill_vector`` is the active hurdle category when the run died, or
    ``"natural_causes"`` when cash went negative with no active hurdle.
    """
    rng = random.Random(seed)
    state = compile_blueprint(blueprint_payload)
    hurdle_months = _hurdle_months(rng, months)
    hurdle_index = 0
    survived = True
    lifespan = 0
    kill_vector: str | None = None

    for month in range(1, months + 1):
        # At a hurdle month: apply the template impact + chosen option.
        if hurdle_index < len(hurdle_months) and month == hurdle_months[hurdle_index]:
            template = HURDLE_TEMPLATES[hurdle_index % len(HURDLE_TEMPLATES)]
            state = apply_event(
                state, {"immediate": template["immediate"]}, month=month
            )
            option = _auto_option(_GENERIC_OPTIONS)
            state.financials.cash += option["cash_impact_monthly"]
            if state.bankrupt:
                kill_vector = template["category"]
                break
            hurdle_index += 1

        state = tick(state, rng)
        lifespan = month
        if state.bankrupt:
            survived = False
            kill_vector = kill_vector or "natural_causes"
            break

    return {
        "seed": seed,
        "survived": survived,
        "lifespan_months": lifespan if not survived else months,
        "kill_vector": kill_vector,
    }


def aggregate_results(outcomes: list[dict[str, Any]]) -> MonteCarloResult:
    """Aggregate sub-run outcomes into a MonteCarloResult (pure)."""
    if not outcomes:
        return MonteCarloResult(
            n_runs=0,
            survival_rate=0.0,
            median_lifespan_months=0,
            p25_lifespan_months=0,
            p75_lifespan_months=0,
            kill_vectors={},
            runs_summary=[],
        )

    lifespans = [int(o["lifespan_months"]) for o in outcomes]
    survived_count = sum(1 for o in outcomes if o["survived"])
    kill_vectors: dict[str, int] = {}
    for o in outcomes:
        if not o["survived"]:
            key = o.get("kill_vector") or "natural_causes"
            kill_vectors[key] = kill_vectors.get(key, 0) + 1

    def percentile(values: list[int], p: float) -> int:
        if not values:
            return 0
        ordered = sorted(values)
        idx = int(p / 100 * (len(ordered) - 1))
        return ordered[idx]

    return MonteCarloResult(
        n_runs=len(outcomes),
        survival_rate=round(survived_count / len(outcomes), 4),
        median_lifespan_months=int(median(lifespans)),
        p25_lifespan_months=percentile(lifespans, 25),
        p75_lifespan_months=percentile(lifespans, 75),
        kill_vectors=kill_vectors,
        runs_summary=[
            MonteCarloRunSummary(
                seed=int(o["seed"]),
                survived=bool(o["survived"]),
                lifespan_months=int(o["lifespan_months"]),
            )
            for o in outcomes
        ],
    )


async def _publish(redis: Redis | None, run_id: str, type_: str, data: Any) -> None:
    if redis is None:
        return
    from contextlib import suppress

    with suppress(Exception):
        await redis.publish(
            _channel(run_id), json.dumps({"type": type_, "data": data})
        )


async def _write_progress(
    redis: Redis | None, run_id: str, completed: int, total: int
) -> None:
    percent = round(completed / total * 100, 1) if total else 0
    payload = json.dumps(
        {"completed": completed, "total": total, "percent": percent}
    )
    if redis is None:
        return
    from contextlib import suppress

    with suppress(Exception):
        await redis.set(_progress_key(run_id), payload, ex=3600)


async def run_monte_carlo_batch(
    *,
    blueprint_payload: dict[str, Any],
    base_seed: int,
    n_runs: int,
    months: int,
    run_id: str,
    redis: Redis | None,
) -> tuple[MonteCarloResult, bool]:
    """Run the full batch — used by the Celery task and tests.

    Redis writes are best-effort; the control flag is checked between sub-runs.
    Returns ``(result, cancelled)``.
    """
    outcomes: list[dict[str, Any]] = []
    cancelled = False
    for i in range(n_runs):
        if redis is not None:
            try:
                flag = await redis.get(_control_key(run_id))
                if flag == b"cancel" or flag == "cancel":
                    cancelled = True
                    break
            except Exception:  # noqa: BLE001
                pass
        seed = base_seed + i
        outcomes.append(run_one(blueprint_payload, seed=seed, months=months))
        await _write_progress(redis, run_id, i + 1, n_runs)
        await _publish(
            redis,
            run_id,
            "progress",
            {
                "completed": i + 1,
                "total": n_runs,
                "percent": round((i + 1) / n_runs * 100, 1),
            },
        )

    return aggregate_results(outcomes), cancelled


def _task(name: str) -> Callable[[Callable[..., Any]], Any]:
    # Celery's untyped decorator returns Any; cast keeps mypy quiet.
    return celery_app.task(name=name)  # type: ignore[no-any-return]


def _run_coro(coro: Any) -> None:
    """Run a coroutine from a sync Celery task.

    In a real worker there is no running loop, so ``asyncio.run`` is correct.
    Under pytest's eager mode the task runs inside the test's event loop,
    where ``asyncio.run`` raises — execute the coroutine on a dedicated
    thread with its own loop and block until it finishes.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
        return

    def _target() -> None:
        asyncio.run(coro)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join()


@_task("forge.monte_carlo")
def run_monte_carlo(run_id: str) -> None:
    """Celery task: load the run, execute the batch, persist the result.

    Each invocation builds its own engine: the module-level ``async_engine``
    binds pooled connections to the first event loop that touches them, but the
    worker runs every task on a fresh ``asyncio.run`` loop, so a shared engine
    leaks connections across loops ("Future attached to a different loop").
    Disposing per task keeps each loop's pool isolated.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.config import get_settings

    async def _run() -> None:
        redis: Redis | None = None
        try:
            settings = get_settings()
            redis = Redis.from_url(settings.redis_url, decode_responses=True)
        except Exception:  # noqa: BLE001 - best-effort
            redis = None

        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with async_session_factory() as session:
                run = await session.get(SimulationRun, run_id)
                if run is None:
                    logger.warning("monte carlo: run not found", run_id=run_id)
                    return
                run.status = RunStatus.RUNNING
                await session.commit()

                from app.models.blueprint import BlueprintVersion
                version = await session.get(BlueprintVersion, run.blueprint_version_id)
                if version is None:
                    run.status = RunStatus.FAILED
                    run.result = {"error": "Blueprint version not found"}
                    await session.commit()
                    return

                n_runs = int(run.config.get("n_runs", 100))
                months = int(run.config.get("months", 24))
                base_seed = run.seed
                try:
                    result, cancelled = await run_monte_carlo_batch(
                        blueprint_payload=dict(version.payload),
                        base_seed=base_seed,
                        n_runs=n_runs,
                        months=months,
                        run_id=run_id,
                        redis=redis,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error("monte carlo batch failed", run_id=run_id, exc_info=True)
                    run.status = RunStatus.FAILED
                    run.result = {"error": str(exc)}
                    run.finished_at = datetime.now(UTC)
                    await session.commit()
                    return

                if cancelled:
                    run.status = RunStatus.CANCELLED
                    run.result = {"cancelled": True, "completed_runs": len(result.runs_summary)}
                else:
                    run.status = RunStatus.COMPLETED
                    run.result = result.model_dump(mode="json")
                run.finished_at = datetime.now(UTC)
                await session.commit()

                await _publish(redis, run_id, "status", {"status": run.status})
                if redis is not None:
                    from contextlib import suppress

                    with suppress(Exception):
                        await redis.close()
        finally:
            await engine.dispose()

    _run_coro(_run())
