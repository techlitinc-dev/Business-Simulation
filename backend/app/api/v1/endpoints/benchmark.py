"""Benchmark endpoints: cohort stats + score percentile."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.services.benchmark.aggregator import get_cohort_stats, score_percentile
from app.services.benchmark.schemas import CohortStats, PercentileResult

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("/cohort", response_model=CohortStats | None)
async def get_cohort(
    db: DbSession,
    industry: str | None = Query(default=None),
    stage: str | None = Query(default=None),
) -> CohortStats | None:
    return await get_cohort_stats(industry, stage, db)


@router.get("/percentile", response_model=PercentileResult)
async def get_percentile(
    db: DbSession,
    score: float = Query(...),
    industry: str | None = Query(default=None),
    stage: str | None = Query(default=None),
) -> PercentileResult:
    return await score_percentile(score, industry, stage, db)
