"""Decision journal response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class JournalEntry(BaseModel):
    """One recorded decision with its score against the run outcome."""

    decision_id: str
    run_id: str
    month: int | None
    option_chosen: str
    option_name: str | None = None
    beat_ai: bool
    actual_outcome: dict[str, Any]
    score: float  # 0.0–1.0


class JournalSummary(BaseModel):
    """Workspace-wide decision quality aggregate."""

    total_decisions: int
    beat_ai_count: int
    beat_ai_pct: float
    summary: str
