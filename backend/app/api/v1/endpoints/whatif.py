"""What-If Lab endpoints: sweeps, breakeven search, version forks."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentWorkspace, DbSession
from app.models.workspace import Workspace
from app.schemas.blueprint import BlueprintVersionResponse
from app.schemas.whatif import SaveVersionRequest
from app.services.blueprint_service import create_version_from_override
from app.services.whatif.breakeven import find_breakeven
from app.services.whatif.schemas import BreakevenRequest, BreakevenResult, SweepRequest, SweepResult
from app.services.whatif.sweep import run_sweep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatif", tags=["whatif"])


def _require_pro(workspace: Workspace) -> None:
    if workspace.plan_tier == "free":
        raise HTTPException(status_code=402, detail="Pro plan required for What-If Lab")


@router.post("/sweep", response_model=SweepResult)
async def sweep_endpoint(
    body: SweepRequest,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> SweepResult:
    """Run a parameter sweep across a range. Pro+ plan required."""
    _require_pro(workspace)
    return await run_sweep(body, db)


@router.post("/breakeven", response_model=BreakevenResult)
async def breakeven_endpoint(
    body: BreakevenRequest,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> BreakevenResult:
    """Find the parameter threshold where survival crosses 50%."""
    _require_pro(workspace)
    return await find_breakeven(body, db)


@router.post("/save-version", response_model=BlueprintVersionResponse, status_code=201)
async def save_version_endpoint(
    body: SaveVersionRequest,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> BlueprintVersionResponse:
    """
    Fork a blueprint version with one parameter override applied.
    Returns the new BlueprintVersion.
    """
    _require_pro(workspace)

    new_version = await create_version_from_override(
        db,
        workspace_id=workspace.id,
        blueprint_id=body.blueprint_id,
        param=body.param,
        value=body.value,
        label=body.version_label,
    )
    logger.info(
        "whatif: saved override version=%s blueprint=%s param=%s",
        new_version.version,
        body.blueprint_id,
        body.param,
    )
    return BlueprintVersionResponse.model_validate(new_version)
