from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.benchmark import BenchmarkSnapshot as BenchmarkModel
from app.services.benchmark.schemas import CohortStats, PercentileResult


async def snapshot_run(
    run_id: str,
    survival_rate: float,
    median_lifespan: float,
    resilience_score: float,
    kill_vectors: list[dict[str, Any]],
    industry: str | None,
    stage: str | None,
    db: AsyncSession,
) -> str:
    """Persist an anonymized benchmark snapshot. Returns snapshot id."""
    snap = BenchmarkModel(
        industry=industry,
        stage=stage,
        survival_rate=survival_rate,
        median_lifespan=median_lifespan,
        resilience_score=resilience_score,
        kill_vectors=kill_vectors[:3] if kill_vectors else [],
    )
    db.add(snap)
    await db.commit()
    await db.refresh(snap)
    return snap.id


async def get_cohort_stats(
    industry: str | None,
    stage: str | None,
    db: AsyncSession,
) -> CohortStats | None:
    """Return aggregated stats for a cohort. Returns None if fewer than 5 samples."""
    q = select(BenchmarkModel).where(BenchmarkModel.opted_in.is_(True))
    if industry:
        q = q.where(BenchmarkModel.industry == industry)
    if stage:
        q = q.where(BenchmarkModel.stage == stage)
    result = await db.execute(q)
    rows = result.scalars().all()

    if len(rows) < 5:
        return None

    scores = sorted(r.resilience_score for r in rows)
    survivals = sorted(r.survival_rate for r in rows)
    lifespans = sorted(r.median_lifespan for r in rows)
    n = len(rows)

    def pct(arr: list[float], p: float) -> float:
        idx = max(0, min(n - 1, int(n * p / 100)))
        return round(arr[idx], 2)

    # Aggregate kill vectors.
    kv_counts: dict[str, int] = {}
    for row in rows:
        for kv in row.kill_vectors or []:
            t = kv.get("type", "unknown")
            kv_counts[t] = kv_counts.get(t, 0) + 1
    top_kvs = [k for k, _ in sorted(kv_counts.items(), key=lambda x: -x[1])[:3]]

    return CohortStats(
        industry=industry,
        stage=stage,
        sample_size=n,
        survival_rate_p25=pct(survivals, 25),
        survival_rate_p50=pct(survivals, 50),
        survival_rate_p75=pct(survivals, 75),
        resilience_score_p25=pct(scores, 25),
        resilience_score_p50=pct(scores, 50),
        resilience_score_p75=pct(scores, 75),
        median_lifespan_p50=pct(lifespans, 50),
        top_kill_vectors=top_kvs,
    )


async def score_percentile(
    score: float,
    industry: str | None,
    stage: str | None,
    db: AsyncSession,
) -> PercentileResult:
    """Return the percentile rank of a score within the cohort."""
    q = select(BenchmarkModel.resilience_score).where(BenchmarkModel.opted_in.is_(True))
    if industry:
        q = q.where(BenchmarkModel.industry == industry)
    if stage:
        q = q.where(BenchmarkModel.stage == stage)
    result = await db.execute(q)
    all_scores = sorted(r[0] for r in result.all())

    n = len(all_scores)
    if n == 0:
        return PercentileResult(
            score=score,
            industry=industry,
            stage=stage,
            percentile=50.0,
            sample_size=0,
            label="No peer data available yet",
        )

    rank = sum(1 for s in all_scores if s < score)
    percentile = round((rank / n) * 100, 1)

    cohort_label = f"{industry or 'all'} {stage or ''} simulations".strip()
    label = f"{percentile:.0f}th percentile vs. {cohort_label}"

    return PercentileResult(
        score=score,
        industry=industry,
        stage=stage,
        percentile=percentile,
        sample_size=n,
        label=label,
    )
