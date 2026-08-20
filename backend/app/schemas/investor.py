from pydantic import BaseModel, Field


class InvestmentTeaser(BaseModel):
    problem: str
    solution: str
    simulated_survival: str  # e.g. "68% 24-month survival across 100 simulated runs"
    key_metrics: list[str] = Field(..., min_length=3, max_length=5)
    ask: str
    risks: list[str] = Field(..., min_length=1, max_length=3)


class PitchSlide(BaseModel):
    slide_number: int
    title: str
    talking_points: list[str] = Field(..., min_length=1, max_length=5)


class PitchDeckOutline(BaseModel):
    slides: list[PitchSlide] = Field(..., min_length=10, max_length=12)
