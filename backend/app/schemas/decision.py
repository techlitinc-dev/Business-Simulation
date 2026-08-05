"""Strategic decision schemas — Format B strategic_options + projections (T24)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrategicOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    cash_impact_monthly: float
    probability_success: float = Field(ge=0, le=1)
    second_order_risk: str = Field(min_length=1)
    required_execution: str = Field(min_length=1)


class StrategicOptionList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    options: list[StrategicOption] = Field(min_length=2, max_length=4)


class OptionProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_id: str
    monthly_cash: list[float]
    end_cash: float
    min_cash: float
    survives: bool
    runway_months: float


class StrategistResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hurdle_id: str
    options: list[StrategicOption]
    projections: list[OptionProjection]
