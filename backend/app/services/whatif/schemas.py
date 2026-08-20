import uuid

from pydantic import BaseModel, Field


class SweepRequest(BaseModel):
    workspace_id: uuid.UUID
    blueprint_id: str
    param: str = Field(
        ...,
        description=(
            "e.g. 'revenue_engine.streams.0.churn_monthly', "
            "'cost_structure.fixed_monthly'"
        ),
    )
    min_value: float
    max_value: float
    steps: int = Field(default=10, ge=2, le=50)
    mc_runs: int = Field(default=20, ge=5, le=100, description="Simulations per grid point")


class SweepGridPoint(BaseModel):
    param_value: float
    survival_rate: float
    median_runway: float
    p25_runway: float
    p75_runway: float


class SweepResult(BaseModel):
    blueprint_id: str
    param: str
    grid: list[SweepGridPoint]
    breakeven_value: float | None = None


class BreakevenRequest(BaseModel):
    workspace_id: uuid.UUID
    blueprint_id: str
    param: str
    search_min: float
    search_max: float
    target_survival: float = Field(default=0.5, ge=0.0, le=1.0)


class BreakevenResult(BaseModel):
    blueprint_id: str
    param: str
    breakeven_value: float
    survival_at_breakeven: float
    message: str
