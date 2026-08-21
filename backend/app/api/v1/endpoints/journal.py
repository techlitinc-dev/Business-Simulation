"""Decision journal + playbook endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentWorkspace, DbSession
from app.core.exceptions import DomainError
from app.services.deep_report.manifest import DataInputKey, SectionDef
from app.services.journal.journal_service import (
    get_run_journal,
    get_workspace_journal_summary,
)
from app.services.journal.schemas import JournalEntry, JournalSummary
from app.services.simulation_service import get_workspace_run

logger = logging.getLogger("forge.journal")

router = APIRouter(prefix="/journal", tags=["journal"])

#: Data inputs the playbook writer consumes from the run.
_PLAYBOOK_INPUTS = [
    DataInputKey.MC_AGGREGATES,
    DataInputKey.FORGE_VULNERABILITIES,
    DataInputKey.EVENTS_DECISIONS,
    DataInputKey.RUN_METADATA,
]


@router.get("/simulations/{run_id}", response_model=list[JournalEntry])
async def run_journal(
    run_id: str, db: DbSession, workspace: CurrentWorkspace
) -> list[JournalEntry]:
    """Journal of every decision made in one run."""
    # 404 for runs outside the workspace (same guard as /simulations/{id}).
    try:
        await get_workspace_run(db, workspace.id, run_id)
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await get_run_journal(run_id, db)


@router.get("/summary", response_model=JournalSummary)
async def workspace_journal(
    db: DbSession, workspace: CurrentWorkspace
) -> JournalSummary:
    """Aggregate decision quality across the workspace's runs."""
    return await get_workspace_journal_summary(str(workspace.id), db)


@router.post("/simulations/{run_id}/playbook", status_code=201)
async def create_playbook(
    run_id: str, db: DbSession, workspace: CurrentWorkspace
) -> dict[str, object]:
    """Generate a reusable playbook from a completed run's post-mortem data."""
    try:
        run = await get_workspace_run(db, workspace.id, run_id)
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    from app.agents.playbook_writer import generate_playbook
    from app.services.deep_report.data_pack import build_data_pack

    section = SectionDef(
        section_number=1,
        title="Playbook",
        page_budget=2,
        data_inputs=_PLAYBOOK_INPUTS,
        prompt_template="playbook_writer.md",
    )
    data_pack = await build_data_pack(section, run_id, db)
    run_summary = {
        "run_id": run.id,
        "status": run.status,
        "outcome": run.result or {},
    }
    playbook = await generate_playbook(data_pack, run_summary)
    return playbook.model_dump()
