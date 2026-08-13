"""Simulation request/response schemas (T25/T26/T27/T28)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SimulationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    months: int = Field(default=24, ge=1, le=120)
    difficulty: Literal["standard", "hard", "nightmare"] = "standard"
    n_runs: int = Field(default=100, ge=1, le=1000)
    # T43 Ghost Mode: required when mode="ghost".
    personality: Literal["aggressive", "conservative", "opportunist"] | None = None


class SimulationStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blueprint_version_id: str = Field(min_length=1)
    mode: Literal["baseline", "stress", "monte_carlo", "ghost"] = "baseline"
    seed: int | None = Field(default=None, ge=0)
    config: SimulationConfig = SimulationConfig()


class ControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["pause", "resume", "cancel"]


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    option_id: str = Field(min_length=1)


class SimulationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: uuid.UUID
    blueprint_version_id: str
    mode: str
    status: str
    seed: int
    current_month: int
    config: dict[str, Any]
    result: dict[str, Any] | None = None
    progress: dict[str, Any] | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class SimulationVisibilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_public: bool


class TickLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    month: int
    kpis: dict[str, Any]


class MonteCarloRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: int
    survived: bool
    lifespan_months: int


class MonteCarloResult(BaseModel):
    """Aggregated outcomes of a Monte Carlo batch (T27)."""

    model_config = ConfigDict(extra="forbid")

    n_runs: int
    survival_rate: float = Field(ge=0, le=1)
    median_lifespan_months: int
    p25_lifespan_months: int
    p75_lifespan_months: int
    kill_vectors: dict[str, int]
    runs_summary: list[MonteCarloRunSummary]
    resilience_score: int = Field(default=0, ge=0, le=100)


class DecisionAppliedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str
    event_id: str
    option_id: str
    run: SimulationRunResponse
