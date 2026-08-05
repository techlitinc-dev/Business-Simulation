"""Format B hurdle schema (spec §10) — without strategic_options (T24 owns those)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImmediateDeltas(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cac_delta_percent: float | None = None
    churn_delta_percent: float | None = None
    new_signups_delta_percent: float | None = None
    team_morale_delta: float | None = None
    cash_burn_delta_monthly: float | None = None
    mrr_delta_percent: float | None = None


class MechanicalImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    immediate: ImmediateDeltas = ImmediateDeltas()
    cascading: dict[str, str] = {}


class HurdleNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    story: str
    source_actor: str
    believability_score: float = Field(ge=0, le=1)


class HurdleEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    trigger_timing: str
    category: Literal["market", "operational", "financial", "black_swan", "internal"]
    narrative: HurdleNarrative
    mechanical_impact: MechanicalImpact = MechanicalImpact()
    ai_game_master_note: str
