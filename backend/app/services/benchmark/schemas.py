from typing import Any

from pydantic import BaseModel


class BenchmarkSnapshot(BaseModel):
    industry: str | None = None
    stage: str | None = None
    survival_rate: float
    median_lifespan: float
    resilience_score: float
    kill_vectors: list[dict[str, Any]] = []


class CohortStats(BaseModel):
    industry: str | None
    stage: str | None
    sample_size: int
    survival_rate_p25: float
    survival_rate_p50: float
    survival_rate_p75: float
    resilience_score_p25: float
    resilience_score_p50: float
    resilience_score_p75: float
    median_lifespan_p50: float
    top_kill_vectors: list[str]


class PercentileResult(BaseModel):
    score: float
    industry: str | None
    stage: str | None
    percentile: float  # 0–100
    sample_size: int
    label: str  # "64th percentile vs. B2B SaaS simulations"
