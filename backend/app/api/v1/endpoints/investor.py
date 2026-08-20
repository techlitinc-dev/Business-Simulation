"""Investor endpoints: generate teaser + pitch deck outline PDFs."""

from __future__ import annotations

import os
import tempfile
from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.investor_tools import (
    generate_pitch_outline,
    generate_teaser,
    pitch_outline_to_pdf,
    teaser_to_pdf,
)
from app.api.deps import CurrentWorkspace, DbSession
from app.services.deep_report.data_pack import build_data_pack
from app.services.deep_report.manifest import DataInputKey, SectionDef

router = APIRouter(prefix="/investor", tags=["investor"])


async def _build_investor_data(run_id: str, db: AsyncSession) -> dict[str, Any]:
    section = SectionDef(
        section_number=1,
        title="Investor Data",
        page_budget=3,
        data_inputs=[
            DataInputKey.TICK_LOGS,
            DataInputKey.MC_AGGREGATES,
            DataInputKey.FORGE_VULNERABILITIES,
            DataInputKey.BLUEPRINT,
            DataInputKey.RUN_METADATA,
        ],
        prompt_template="investment_teaser.md",
    )
    return await build_data_pack(section, run_id, db)


def _write_temp_pdf(pdf_bytes: bytes, prefix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".pdf", prefix=prefix)
    os.close(fd)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return path


@router.post("/runs/{run_id}/teaser")
async def generate_teaser_endpoint(
    run_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> FileResponse:
    data = await _build_investor_data(run_id, db)
    teaser = await generate_teaser(data)
    pdf_bytes = teaser_to_pdf(teaser, workspace.name, run_id)
    path = _write_temp_pdf(pdf_bytes, f"teaser_{run_id}_")
    return FileResponse(path, media_type="application/pdf", filename=f"teaser_{run_id}.pdf")


@router.post("/runs/{run_id}/pitch-deck")
async def generate_pitch_endpoint(
    run_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> FileResponse:
    data = await _build_investor_data(run_id, db)
    outline = await generate_pitch_outline(data)
    pdf_bytes = pitch_outline_to_pdf(outline, workspace.name, run_id)
    path = _write_temp_pdf(pdf_bytes, f"pitch_{run_id}_")
    return FileResponse(path, media_type="application/pdf", filename=f"pitch_outline_{run_id}.pdf")
