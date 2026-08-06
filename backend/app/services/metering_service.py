"""Usage metering + plan-limit enforcement (T41)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PlanLimitExceeded
from app.models.billing import UsageRecord
from app.models.workspace import Workspace
from app.services.plans import get_plan

Metric = Literal["runs", "mc_ticks", "llm_tokens"]

_COLUMN_BY_METRIC: dict[Metric, str] = {
    "runs": "runs_used",
    "mc_ticks": "mc_ticks_used",
    "llm_tokens": "llm_tokens_used",
}


def current_period() -> str:
    """The current UTC month as ``YYYY-MM``."""
    return datetime.now(UTC).strftime("%Y-%m")


def _as_uuid(workspace_id: uuid.UUID | str) -> uuid.UUID:
    return workspace_id if isinstance(workspace_id, uuid.UUID) else uuid.UUID(workspace_id)


async def get_current_usage(
    db: AsyncSession, workspace_id: uuid.UUID | str
) -> UsageRecord:
    """Return the workspace's UsageRecord for the current month (get-or-create)."""
    period = current_period()
    wid = _as_uuid(workspace_id)
    record = await db.scalar(
        select(UsageRecord).where(
            UsageRecord.workspace_id == wid,
            UsageRecord.period == period,
        )
    )
    if record is None:
        record = UsageRecord(
            workspace_id=wid,
            period=period,
            runs_used=0,
            mc_ticks_used=0,
            llm_tokens_used=0,
        )
        db.add(record)
        await db.flush()
        await db.commit()
        await db.refresh(record)
    return record


async def increment(
    db: AsyncSession,
    workspace_id: uuid.UUID | str,
    metric: Metric,
    amount: int = 1,
) -> UsageRecord:
    """Increment a metric's counter for the current period."""
    record = await get_current_usage(db, workspace_id)
    column = _COLUMN_BY_METRIC[metric]
    setattr(record, column, getattr(record, column) + amount)
    await db.commit()
    await db.refresh(record)
    return record


async def check_limit(
    db: AsyncSession,
    workspace_id: uuid.UUID | str,
    metric: Metric,
    amount: int = 1,
) -> None:
    """Raise ``PlanLimitExceeded`` when the workspace's tier can't afford ``amount``."""
    workspace = await db.get(Workspace, _as_uuid(workspace_id))
    tier = workspace.plan_tier if workspace is not None else "free"
    plan = get_plan(tier)

    limit_field = {
        "runs": "runs_per_month",
        "mc_ticks": "monte_carlo_runs_per_batch",
        "llm_tokens": "llm_tokens_per_month",
    }[metric]
    limit = getattr(plan, limit_field)
    if limit == -1:
        return  # unlimited

    record = await get_current_usage(db, workspace_id)
    used = getattr(record, _COLUMN_BY_METRIC[metric])
    if used + amount > limit:
        raise PlanLimitExceeded(metric=metric, limit=limit, used=used, tier=tier)
