"""
Celery periodic task: re-simulate each blueprint that has actuals,
compare resilience score, dispatch alert if drop > threshold.
"""
from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from typing import Any

import structlog
from sqlalchemy import select

from app.models.actuals import ActualsRecord
from app.services.actuals.alert_service import dispatch_drift_alert, should_alert
from app.services.actuals.variance import compute_variance
from app.workers.celery_app import celery_app

logger = structlog.get_logger("forge.drift_monitor")


def _task(name: str) -> Callable[[Callable[..., Any]], Any]:
    # Celery's untyped decorator returns Any; cast keeps mypy quiet.
    return celery_app.task(name=name)  # type: ignore[no-any-return]


def _run_coro(coro: Any) -> Any:
    """Run a coroutine from a sync Celery task and return its result.

    In a real worker there is no running loop, so ``asyncio.run`` is correct.
    Under pytest's eager mode the task runs inside the test's event loop,
    where ``asyncio.run`` raises — execute the coroutine on a dedicated
    thread with its own loop and block until it finishes.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}

    def _target() -> None:
        result["value"] = asyncio.run(coro)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join()
    return result.get("value")


@_task("forge.check_all_blueprints")
def check_all_blueprints() -> int:
    """Check all blueprints with actuals for resilience drift.

    Returns the number of blueprints checked.
    """

    async def _run() -> int:
        # Per-task engine: the module-level ``async_engine`` binds pooled
        # connections to the first event loop that touches them, but the worker
        # runs every task on a fresh ``asyncio.run`` loop, so a shared engine
        # leaks connections across loops ("Future attached to a different
        # loop"). Disposing per task keeps each loop's pool isolated.
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from app.core.config import get_settings

        engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with session_factory() as db:
                result = await db.execute(
                    select(ActualsRecord.blueprint_id, ActualsRecord.workspace_id).distinct()
                )
                pairs = result.all()

            logger.info("drift monitor: checking blueprints", count=len(pairs))

            checked = 0
            for blueprint_id, workspace_id in pairs:
                try:
                    async with session_factory() as db:
                        delta = await compute_variance(blueprint_id, workspace_id, db, mc_runs=30)
                        if await should_alert(delta):
                            await dispatch_drift_alert(delta, workspace_id, db)
                            logger.info(
                                "drift monitor: alert triggered",
                                blueprint_id=blueprint_id,
                                score_delta=delta.score_delta,
                            )
                        else:
                            logger.debug(
                                "drift monitor: no alert",
                                blueprint_id=blueprint_id,
                                score_delta=delta.score_delta,
                            )
                        checked += 1
                except Exception:  # noqa: BLE001 - one bad blueprint must not stop the sweep
                    logger.error(
                        "drift monitor: error checking blueprint",
                        blueprint_id=blueprint_id,
                        exc_info=True,
                    )

            logger.info("drift monitor: done", checked=checked)
            return checked
        finally:
            await engine.dispose()

    return _run_coro(_run())  # type: ignore[no-any-return]
