from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio, PortfolioMembership
from app.models.simulation import SimulationRun
from app.services.portfolio.schemas import PortfolioSummary, WorkspaceSummary


async def create_portfolio(
    name: str, owner_user_id: uuid.UUID, db: AsyncSession
) -> Portfolio:
    portfolio = Portfolio(name=name, owner_user_id=owner_user_id)
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return portfolio


async def add_workspace(
    portfolio_id: str, workspace_id: uuid.UUID, label: str, db: AsyncSession
) -> PortfolioMembership:
    membership = PortfolioMembership(
        portfolio_id=portfolio_id,
        workspace_id=workspace_id,
        label=label or str(workspace_id),
    )
    db.add(membership)
    await db.commit()
    return membership


async def remove_workspace(
    portfolio_id: str, workspace_id: uuid.UUID, db: AsyncSession
) -> None:
    result = await db.execute(
        select(PortfolioMembership).where(
            PortfolioMembership.portfolio_id == portfolio_id,
            PortfolioMembership.workspace_id == workspace_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership:
        await db.delete(membership)
        await db.commit()


async def get_portfolio_summary(
    portfolio_id: str, db: AsyncSession
) -> PortfolioSummary | None:
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id)
        .execution_options(populate_existing=True)
    )
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        return None

    workspace_summaries: list[WorkspaceSummary] = []
    for membership in portfolio.memberships:
        ws_id = membership.workspace_id
        # Get latest completed run for this workspace.
        run_result = await db.execute(
            select(SimulationRun)
            .where(SimulationRun.workspace_id == ws_id)
            .order_by(SimulationRun.created_at.desc())
            .limit(1)
        )
        latest_run = run_result.scalar_one_or_none()

        score = None
        survival = None
        last_run_at = None
        drift_alert = False

        if latest_run is not None and latest_run.result:
            mc = latest_run.result
            survival = mc.get("survival_rate")
            score = mc.get("resilience_score")
            last_run_at = (
                latest_run.created_at.isoformat() if latest_run.created_at else None
            )

        workspace_summaries.append(
            WorkspaceSummary(
                workspace_id=str(ws_id),
                label=membership.label or str(ws_id),
                resilience_score=round(float(score), 1) if score is not None else None,
                survival_rate=survival,
                drift_alert=drift_alert,
                last_run_at=last_run_at,
            )
        )

    scores = [
        ws.resilience_score for ws in workspace_summaries if ws.resilience_score is not None
    ]
    avg = round(sum(scores) / len(scores), 1) if scores else None

    return PortfolioSummary(
        portfolio_id=portfolio_id,
        name=portfolio.name,
        member_count=len(workspace_summaries),
        workspaces=sorted(
            workspace_summaries,
            key=lambda w: w.resilience_score if w.resilience_score is not None else -1,
            reverse=True,
        ),
        avg_resilience_score=avg,
    )
