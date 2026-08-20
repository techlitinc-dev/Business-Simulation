"""Data room endpoints: create expiring bundles, download, revoke."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import CurrentWorkspace, DbSession
from app.services.dataroom.dataroom_service import (
    create_dataroom,
    get_dataroom,
    record_view,
    revoke_dataroom,
)
from app.services.dataroom.schemas import DataRoomCreate

router = APIRouter(prefix="/dataroom", tags=["dataroom"])


@router.post("/", status_code=201)
async def create_data_room(
    body: DataRoomCreate,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> dict[str, Any]:
    from app.services.deep_report.data_pack import (
        _extract_mc_aggregates,
        _fetch_run,
        _fetch_tick_logs,
    )

    run = await _fetch_run(body.run_id, db)
    ticks = await _fetch_tick_logs(body.run_id, db)
    mc = _extract_mc_aggregates(run) or {}
    return await create_dataroom(
        run_id=body.run_id,
        label=body.label,
        expiry_days=body.expiry_days,
        pdf_path=None,
        tick_logs=ticks,
        mc_aggregates=mc,
        workspace_name=workspace.name,
        db=db,
    )


@router.get("/{token}/download")
async def download_data_room(token: str) -> FileResponse:
    meta = await get_dataroom(token)
    if not meta:
        raise HTTPException(status_code=410, detail="Data room link has expired or been revoked")
    await record_view(token)
    return FileResponse(
        meta["bundle_path"],
        media_type="application/zip",
        filename=f"data_room_{token}.zip",
    )


@router.delete("/{token}")
async def revoke_data_room(
    token: str,
    workspace: CurrentWorkspace,
) -> dict[str, Any]:
    await revoke_dataroom(token)
    return {"revoked": True}
