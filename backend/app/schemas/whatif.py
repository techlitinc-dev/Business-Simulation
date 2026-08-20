from __future__ import annotations

from pydantic import BaseModel

from app.services.whatif.schemas import (
    BreakevenRequest,
    BreakevenResult,
    SweepRequest,
    SweepResult,
)

__all__ = [
    "SweepRequest",
    "SweepResult",
    "BreakevenRequest",
    "BreakevenResult",
    "SaveVersionRequest",
]


class SaveVersionRequest(BaseModel):
    blueprint_id: str
    param: str
    value: float
    version_label: str = "What-If Override"
