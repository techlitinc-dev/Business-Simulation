from typing import Any

from pydantic import BaseModel, Field


class ExecutiveSummarySection(BaseModel):
    verdict: str = Field(..., description="One-sentence pass/fail verdict")
    headline_metrics: list[str] = Field(..., min_length=3, max_length=5)
    narrative: str = Field(..., min_length=100)
    risk_level: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")


class FinancialNarrativeSection(BaseModel):
    month_stories: list[str] = Field(..., min_length=1, max_length=24,
        description="One narrative sentence per simulated month")
    key_inflection_months: list[int]
    overall_narrative: str = Field(..., min_length=200)


class WeaknessRegisterSection(BaseModel):
    weaknesses: list[dict[str, Any]] = Field(
        ..., description="Each: {title, severity, description, mitigation}"
    )
    summary: str


class ActionPlanSection(BaseModel):
    actions: list[dict[str, Any]] = Field(..., min_length=3, max_length=10,
        description="Each: {priority, action, owner, timeline, expected_impact}")
    narrative: str


class GenericNarrativeSection(BaseModel):
    """Fallback schema for sections that only need narrative text."""
    narrative: str = Field(..., min_length=50)
    key_points: list[str] = Field(..., min_length=1)
