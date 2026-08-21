"""Industry pack registry — declarative packs applied to blueprints at creation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IndustryPack:
    id: str
    name: str
    description: str
    engine_params: dict[str, Any]       # parameter overrides applied to blueprint
    blueprint_template: dict[str, Any]  # base blueprint payload
    hurdle_library: list[dict[str, Any]]  # hurdle event templates
    report_manifest_variant: str = "resilience_audit"
    vertical_kpis: list[str] = field(default_factory=list)


PACK_REGISTRY: dict[str, IndustryPack] = {}


def register_pack(pack: IndustryPack) -> None:
    PACK_REGISTRY[pack.id] = pack


def get_pack(pack_id: str) -> IndustryPack | None:
    return PACK_REGISTRY.get(pack_id)


def list_packs() -> list[dict[str, str]]:
    return [
        {"id": p.id, "name": p.name, "description": p.description}
        for p in PACK_REGISTRY.values()
    ]
