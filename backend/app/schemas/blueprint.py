"""Blueprint (Format A) Pydantic v2 schemas + CRUD request/response DTOs.

Format A is the canonical blueprint contract shared by the API (T17), the
engine compiler (T11), and the AI bridge (T22+). Every model forbids extra
fields so malformed payloads fail loudly instead of being silently dropped.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HTML_TAG_RE = re.compile(r"<[^>]*>")


def strip_html(value: str) -> str:
    """Strip HTML tags from a plain-text field (XSS defense)."""
    return _HTML_TAG_RE.sub("", value).strip()


class BusinessProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_type: str
    stage: str
    industry: str
    geography: str


class RevenueStream(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    pricing_model: str = Field(min_length=1, max_length=120)
    price_point: float = Field(gt=0)
    projected_customers_month_12: int = Field(ge=0)
    ltv: float = Field(ge=0)
    cac: float = Field(ge=0)
    churn_monthly: float = Field(ge=0, le=1)


class RevenueEngine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    streams: list[RevenueStream]


class TeamMember(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(min_length=1, max_length=120)
    salary_annual: float = Field(ge=0)
    hire_month: int = Field(ge=0)


class CostStructure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixed_monthly: float = Field(ge=0)
    variable_per_unit: float = Field(ge=0)
    team: list[TeamMember]
    burn_rate_month_1: float = Field(ge=0)


class FundingRound(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: int = Field(ge=0)
    amount: float = Field(gt=0)


class Financials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_capital: float = Field(ge=0)
    funding_rounds: list[FundingRound]
    target_runway_months: int = Field(ge=1)


class Vulnerability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["liquidity", "market", "operational", "competitive", "regulatory"]
    severity: Literal["low", "medium", "high"]
    description: str
    mitigation_suggestion: str


class SimulationParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time_step: Literal["monthly"] = "monthly"
    monte_carlo_runs: int = 100
    random_seed: int | None = None


class BlueprintPayload(BaseModel):
    """Root Format A document."""

    model_config = ConfigDict(extra="forbid")

    blueprint_version: str = "1.0"
    business_profile: BusinessProfile
    revenue_engine: RevenueEngine
    cost_structure: CostStructure
    financials: Financials
    identified_vulnerabilities: list[Vulnerability]
    simulation_parameters: SimulationParameters


# ---------------------------------------------------------------------------
# CRUD DTOs (T17)
# ---------------------------------------------------------------------------


class BlueprintCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    industry: str = Field(min_length=1, max_length=120)
    stage: str = Field(min_length=1, max_length=120)
    payload: BlueprintPayload

    @field_validator("name", "industry", "stage")
    @classmethod
    def strip_html_fields(cls, value: str) -> str:
        stripped = strip_html(value)
        if not stripped:
            raise ValueError("must not contain only HTML tags")
        return stripped


class BlueprintUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    industry: str | None = Field(default=None, min_length=1, max_length=120)
    stage: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("name", "industry", "stage")
    @classmethod
    def strip_html_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = strip_html(value)
        if not stripped:
            raise ValueError("must not contain only HTML tags")
        return stripped


class BlueprintVersionCreate(BaseModel):
    payload: BlueprintPayload


class BlueprintVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    blueprint_id: str
    version: int
    payload: BlueprintPayload
    vulnerabilities: list[dict[str, object]] = []
    created_at: datetime


class BlueprintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: uuid.UUID
    name: str
    industry: str
    stage: str
    current_version: int
    created_at: datetime
    updated_at: datetime


class BlueprintDetailResponse(BlueprintResponse):
    payload: BlueprintPayload
    vulnerabilities: list[dict[str, object]] = []


class VulnerabilityItem(BaseModel):
    type: Literal[
        "liquidity",
        "concentration",
        "unit_economics",
        "market",
        "operational",
        "team",
        "regulatory",
    ]
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    mitigation_suggestion: str


class ForgeReviewResponse(BaseModel):
    overall_assessment: str
    identified_vulnerabilities: list[VulnerabilityItem]
    reviewed_version: int
    llm_model: str
    tokens_used: int


class ForgeReviewLLMResponse(BaseModel):
    """What the LLM emits — server fills reviewed_version / llm_model / tokens_used."""

    overall_assessment: str
    identified_vulnerabilities: list[VulnerabilityItem]
