"""Actuals endpoints: CSV upload, variance report, history."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.agents.variance_narrator import narrate_variance
from app.api.deps import CurrentWorkspace, DbSession
from app.models.actuals import ActualsRecord
from app.services.actuals.importer import import_actuals
from app.services.actuals.schemas import ActualsUploadRequest, ActualsUploadResult
from app.services.actuals.variance import compute_variance

router = APIRouter(prefix="/actuals", tags=["actuals"])


@router.post("/upload", response_model=ActualsUploadResult)
async def upload_actuals(
    body: ActualsUploadRequest,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> ActualsUploadResult:
    return await import_actuals(body, workspace.id, db)


@router.get("/{blueprint_id}/variance")
async def get_variance(
    blueprint_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> dict[str, object]:
    try:
        delta = await compute_variance(blueprint_id, workspace.id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    narrative = await narrate_variance(delta)
    return {"delta": delta.__dict__, "narrative": narrative.model_dump()}


@router.get("/{blueprint_id}/history")
async def get_actuals_history(
    blueprint_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> list[dict[str, object]]:
    result = await db.execute(
        select(ActualsRecord)
        .where(
            ActualsRecord.blueprint_id == blueprint_id,
            ActualsRecord.workspace_id == workspace.id,
        )
        .order_by(ActualsRecord.month)
    )
    records = result.scalars().all()
    return [
        {"month": r.month, "period_label": r.period_label, **r.fields}
        for r in records
    ]
