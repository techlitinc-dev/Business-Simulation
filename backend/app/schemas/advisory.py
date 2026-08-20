from typing import Literal

from pydantic import BaseModel, Field


class PersonaReview(BaseModel):
    persona: Literal["CFO", "CMO", "RiskAuditor", "Operator"]
    verdict: str = Field(..., description="One-sentence verdict")
    top_concerns: list[str] = Field(..., min_length=1, max_length=5)
    opportunities: list[str] = Field(..., min_length=0, max_length=3)
    questions_for_founder: list[str] = Field(..., min_length=1, max_length=3)
    confidence_level: Literal["LOW", "MEDIUM", "HIGH"]


class BoardSummary(BaseModel):
    consensus_verdict: str
    points_of_agreement: list[str] = Field(..., min_length=1)
    points_of_conflict: list[str]
    top_priority_action: str
    overall_risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
