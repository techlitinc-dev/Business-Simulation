from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.deep_report.manifest import SectionDef


async def build_data_pack(
    section: SectionDef, run_id: str, db: AsyncSession
) -> dict[str, Any]:
    """
    Assemble the deterministic data pack for a single section.
    Stub: returns empty keyed dict. Fleshed out on Day 02.
    """
    return {key.value: None for key in section.data_inputs}
