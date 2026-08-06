"""Admin analytics service (T46) — aggregate queries + MRR estimate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Subscription, UsageRecord
from app.models.simulation import SimulationRun
from app.models.user import User
from app.models.workspace import Membership, Workspace
from app.schemas.admin import (
    AdminStatsResponse,
    AdminUserItem,
    AdminUserListResponse,
    AdminWorkspaceItem,
    AdminWorkspaceListResponse,
)
from app.services.metering_service import current_period
from app.services.plans import get_plans

_PAGE_SIZE = 20


async def admin_stats(db: AsyncSession) -> AdminStatsResponse:
    """Platform-wide aggregates (T46)."""
    total_users = int(await db.scalar(select(func.count(User.id))) or 0)
    users_30d = int(
        await db.scalar(
            select(func.count(User.id)).where(
                User.created_at >= datetime.now(UTC) - timedelta(days=30)
            )
        )
        or 0
    )
    total_workspaces = int(await db.scalar(select(func.count(Workspace.id))) or 0)
    workspaces_30d = int(
        await db.scalar(
            select(func.count(Workspace.id)).where(
                Workspace.created_at >= datetime.now(UTC) - timedelta(days=30)
            )
        )
        or 0
    )

    # Active subscriptions per tier + MRR estimate from PLANS prices.
    tier_rows = await db.execute(
        select(Subscription.tier, func.count(Subscription.id))
        .where(Subscription.status == "active")
        .group_by(Subscription.tier)
    )
    subscriptions_by_tier: dict[str, int] = {"free": 0, "pro": 0, "enterprise": 0}
    for tier, count in tier_rows.all():
        subscriptions_by_tier[tier] = int(count)

    plans = get_plans()
    mrr = sum(
        subscriptions_by_tier.get(tier, 0) * plan.price_usd
        for tier, plan in plans.items()
    )

    # Current-month usage aggregates.
    period = current_period()
    runs = int(
        await db.scalar(
            select(func.sum(UsageRecord.runs_used)).where(
                UsageRecord.period == period
            )
        )
        or 0
    )
    mc_ticks = int(
        await db.scalar(
            select(func.sum(UsageRecord.mc_ticks_used)).where(
                UsageRecord.period == period
            )
        )
        or 0
    )
    llm_tokens = int(
        await db.scalar(
            select(func.sum(UsageRecord.llm_tokens_used)).where(
                UsageRecord.period == period
            )
        )
        or 0
    )

    return AdminStatsResponse(
        total_users=total_users,
        users_last_30d=users_30d,
        total_workspaces=total_workspaces,
        workspaces_last_30d=workspaces_30d,
        subscriptions_by_tier=subscriptions_by_tier,
        mrr_estimate_usd=mrr,
        runs_this_month=runs,
        monte_carlo_ticks_this_month=mc_ticks,
        llm_tokens_this_month=llm_tokens,
    )


async def admin_users(
    db: AsyncSession, *, page: int = 1, q: str | None = None
) -> AdminUserListResponse:
    query = select(User)
    count_query = select(func.count()).select_from(User)
    if q:
        pattern = f"%{q.lower()}%"
        query = query.where(func.lower(User.email).like(pattern))
        count_query = count_query.where(func.lower(User.email).like(pattern))

    total = int(await db.scalar(count_query) or 0)
    rows = await db.scalars(
        query.order_by(User.created_at.desc())
        .offset((page - 1) * _PAGE_SIZE)
        .limit(_PAGE_SIZE)
    )
    users = rows.all()

    # workspace_count per user.
    wc_rows = await db.execute(
        select(Membership.user_id, func.count(Membership.workspace_id))
        .group_by(Membership.user_id)
    )
    counts = {str(uid): int(c) for uid, c in wc_rows.all()}

    items = [
        AdminUserItem(
            id=str(u.id),
            email=u.email,
            name=u.name,
            is_admin=u.is_admin,
            is_verified=u.is_verified,
            created_at=u.created_at,
            workspace_count=counts.get(str(u.id), 0),
        )
        for u in users
    ]
    return AdminUserListResponse(items=items, total=total, page=page)


async def admin_workspaces(
    db: AsyncSession, *, page: int = 1
) -> AdminWorkspaceListResponse:
    count_query = select(func.count()).select_from(Workspace)
    total = int(await db.scalar(count_query) or 0)

    rows = await db.execute(
        select(
            Workspace,
            func.count(func.distinct(Membership.user_id)),
            func.count(func.distinct(SimulationRun.id)),
        )
        .outerjoin(Membership, Membership.workspace_id == Workspace.id)
        .outerjoin(SimulationRun, SimulationRun.workspace_id == Workspace.id)
        .group_by(Workspace.id)
        .order_by(Workspace.created_at.desc())
        .offset((page - 1) * _PAGE_SIZE)
        .limit(_PAGE_SIZE)
    )
    items = [
        AdminWorkspaceItem(
            id=str(ws.id),
            name=ws.name,
            slug=ws.slug,
            plan_tier=ws.plan_tier,
            member_count=int(member_count),
            runs_count=int(runs_count),
            created_at=ws.created_at,
        )
        for ws, member_count, runs_count in rows.all()
    ]
    return AdminWorkspaceListResponse(items=items, total=total, page=page)
