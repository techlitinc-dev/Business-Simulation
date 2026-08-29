"""Industry pack endpoints — list packs and fetch pack details."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

# Importing registers the packs in the registry (module side-effect).
import app.services.industry_packs.ecommerce_pack  # noqa: F401
import app.services.industry_packs.saas_pack  # noqa: F401
from app.api.deps import CurrentUser
from app.services.industry_packs.blueprint_template import build_blueprint_from_pack
from app.services.industry_packs.pack_registry import get_pack, list_packs

router = APIRouter(prefix="/industry-packs", tags=["industry-packs"])


@router.get("")
@router.get("/")
async def list_industry_packs(user: CurrentUser) -> list[dict[str, str]]:
    """List available packs (id, name, description).

    Registered at both ``/industry-packs`` and ``/industry-packs/`` so clients
    don't hit a 307 redirect from a trailing slash (Day 31 checklist).
    """
    return list_packs()


@router.get("/{pack_id}")
async def get_industry_pack(pack_id: str, user: CurrentUser) -> dict[str, Any]:
    """Fetch a pack's engine params, hurdle library, and vertical KPIs."""
    pack = get_pack(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")
    return {
        "id": pack.id,
        "name": pack.name,
        "description": pack.description,
        "engine_params": pack.engine_params,
        "hurdle_library": pack.hurdle_library,
        "vertical_kpis": pack.vertical_kpis,
        "blueprint_template": build_blueprint_from_pack(pack).model_dump(mode="json"),
    }
