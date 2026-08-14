"""Report (Format C) schemas — resilience audit, optimizations, comparison."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class KillVector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cause: str
    count: int
    pct: float  # percent of failures


class SurvivalMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    survival_rate: float = Field(ge=0, le=1)
    runs_total: int
    runs_survived: int
    median_lifespan_months: int
    kill_vectors: list[KillVector]


class Weakness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    title: str
    detail: str


class OptimizationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tweak_key: str
    recommendation: str
    implementation_cost: str
    impact_on_survival_rate: float  # percentage points, engine-measured
    trade_off: str


class CounterFactualInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    deltas: list[dict[str, Any]] = []


class ReportContent(BaseModel):
    """The content_json payload of a persisted Report (Format C)."""

    model_config = ConfigDict(extra="forbid")

    survival: SurvivalMetrics
    weaknesses: list[Weakness] = []
    optimizations: list[OptimizationEntry] = []
    counter_factual: CounterFactualInsight = CounterFactualInsight(text="")
    blueprint_version: int = 1
    resilience_score: int = 0


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    type: str
    content_md: str
    content_json: dict[str, Any]
    pdf_path: str | None = None
    created_at: datetime


class LeaderboardEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int
    run_id: str
    workspace_name: str
    blueprint_name: str
    resilience_score: int
    survival_rate: float
    median_lifespan_months: int
    completed_at: datetime
    # T44: share token of the run's public report — null when the run has no
    # shared report, in which case the frontend shows the row as non-clickable.
    share_token: str | None = None


class LeaderboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[LeaderboardEntry]


class SharedReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blueprint_name: str
    completed_at: datetime
    content_md: str
    content_json: dict[str, Any]


# ---------------------------------------------------------------------------
# T31 — post-mortem output
# ---------------------------------------------------------------------------


class TweakResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tweak_key: str
    label: str
    delta_pp: float
    baseline_survival: float
    tweaked_survival: float


class PostMortemOutput(BaseModel):
    """What the LLM emits for the Format C AI sections."""

    model_config = ConfigDict(extra="forbid")

    optimizations: list[dict[str, str]] = Field(
        description="[{recommendation, implementation_cost, trade_off, tweak_key}]"
    )
    counter_factual_insight: str
    blueprint_v2_suggestions: list[str]


# ---------------------------------------------------------------------------
# T33 — comparison
# ---------------------------------------------------------------------------


class RunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    blueprint_version_id: str
    blueprint_version: int
    survival_rate: float
    median_lifespan_months: int
    resilience_score: int
    top_kill_vector: str


class KillVectorChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cause: str
    pct_a: float
    pct_b: float
    delta_pp: float


class ComparisonDeltas(BaseModel):
    model_config = ConfigDict(extra="forbid")

    survival_rate_pp: float
    median_lifespan_months: int
    resilience_score_pp: int


class ComparisonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    a: RunSummary
    b: RunSummary
    deltas: ComparisonDeltas
    kill_vector_changes: list[KillVectorChange]
    verdict: Literal["improved", "regressed", "unchanged"]
