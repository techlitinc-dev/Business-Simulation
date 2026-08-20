"""Portfolio endpoints: create, summarize, manage member workspaces."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, DbSession
from app.services.portfolio.portfolio_service import (
    add_workspace,
    create_portfolio,
    get_portfolio_summary,
    remove_workspace,
)
from app.services.portfolio.schemas import PortfolioCreate, PortfolioSummary

router = APIRouter(prefix="/portfolios", tags=["portfolio"])


@router.post("/", status_code=201)
async def create(
    body: PortfolioCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    pf = await create_portfolio(body.name, current_user.id, db)
    return {"portfolio_id": pf.id, "name": pf.name}


@router.get("/{portfolio_id}/summary", response_model=PortfolioSummary)
async def summary(
    portfolio_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> PortfolioSummary:
    result = await get_portfolio_summary(portfolio_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return result


@router.post("/{portfolio_id}/workspaces", status_code=201)
async def add_ws(
    portfolio_id: str,
    db: DbSession,
    current_user: CurrentUser,
    workspace_id: uuid.UUID,
    label: str = "",
) -> dict[str, Any]:
    await add_workspace(portfolio_id, workspace_id, label, db)
    return {"added": str(workspace_id)}


@router.delete("/{portfolio_id}/workspaces/{workspace_id}")
async def remove_ws(
    portfolio_id: str,
    workspace_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    await remove_workspace(portfolio_id, workspace_id, db)
    return {"removed": str(workspace_id)}
