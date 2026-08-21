"""Export endpoints — CSV downloads for run ticks and Monte Carlo aggregates."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Response

from app.api.deps import CurrentWorkspace, DbSession
from app.core.exceptions import DomainError
from app.services.deep_report.data_pack import build_data_pack
from app.services.deep_report.manifest import DataInputKey, SectionDef
from app.services.integrations.csv_exporter import mc_to_csv, ticks_to_csv
from app.services.simulation_service import get_workspace_run

logger = logging.getLogger("forge.export")

router = APIRouter(prefix="/export", tags=["export"])


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


async def _guard_run(db: DbSession, workspace: CurrentWorkspace, run_id: str) -> None:
    """404 for runs outside the workspace (same guard as /simulations/{id})."""
    try:
        await get_workspace_run(db, workspace.id, run_id)
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/runs/{run_id}/ticks.csv")
async def export_ticks(
    run_id: str, db: DbSession, workspace: CurrentWorkspace
) -> Response:
    """CSV of every persisted tick's KPIs for a run."""
    await _guard_run(db, workspace, run_id)
    section = SectionDef(
        section_number=1,
        title="Export",
        page_budget=1,
        data_inputs=[DataInputKey.TICK_LOGS],
        prompt_template="export.md",
    )
    pack = await build_data_pack(section, run_id, db)
    ticks = pack.get(DataInputKey.TICK_LOGS.value) or []
    return _csv_response(ticks_to_csv(ticks), f"ticks_{run_id}.csv")


@router.get("/runs/{run_id}/mc.csv")
async def export_mc(
    run_id: str, db: DbSession, workspace: CurrentWorkspace
) -> Response:
    """CSV of a Monte Carlo run's aggregate survival statistics."""
    await _guard_run(db, workspace, run_id)
    section = SectionDef(
        section_number=1,
        title="Export",
        page_budget=1,
        data_inputs=[DataInputKey.MC_AGGREGATES],
        prompt_template="export.md",
    )
    pack = await build_data_pack(section, run_id, db)
    mc = pack.get(DataInputKey.MC_AGGREGATES.value) or {}
    return _csv_response(mc_to_csv(mc), f"mc_{run_id}.csv")
