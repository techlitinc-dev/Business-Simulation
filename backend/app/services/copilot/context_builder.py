from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.deep_report.data_pack import build_data_pack
from app.services.deep_report.manifest import DataInputKey, SectionDef


async def build_copilot_context(run_id: str, db: AsyncSession) -> dict[str, Any]:
    """Build a concise grounding context from run data for the copilot."""
    section = SectionDef(
        section_number=1,
        title="Copilot Context",
        page_budget=5,
        data_inputs=[
            DataInputKey.TICK_LOGS,
            DataInputKey.MC_AGGREGATES,
            DataInputKey.CHRONICLE,
            DataInputKey.EVENTS_DECISIONS,
            DataInputKey.FORGE_VULNERABILITIES,
            DataInputKey.RUN_METADATA,
        ],
        prompt_template="copilot_system.md",
    )
    return await build_data_pack(section, run_id, db)
