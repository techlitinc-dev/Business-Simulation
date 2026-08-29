# Day 20 — F-05: Cohort Benchmark Aggregation Service

## Feature
F-05: Cohort Benchmarks

## Goal
Implement a purely deterministic aggregation service. When a run completes and the user has opted in, snapshot anonymized stats. `get_cohort_stats()` returns percentile distributions sliced by industry and stage. `score_percentile()` returns the user's rank vs peers.

## Prerequisites
- Existing `SimulationRun`, `Report` models
- Onboarding fields on user/workspace (industry, stage — T36)
- No LLM needed

---

## Step 1 — DB Model

`backend/app/models/benchmark.py`:
```python
from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class BenchmarkSnapshot(Base):
    __tablename__ = "benchmark_snapshots"

    id = Column(String, primary_key=True, default=lambda: f"bm_{uuid.uuid4().hex[:12]}")
    # Anonymized — no workspace/user id stored
    industry = Column(String, nullable=True, index=True)
    stage = Column(String, nullable=True, index=True)          # "idea", "pre-seed", "seed", "series-a"
    survival_rate = Column(Float, nullable=False)
    median_lifespan = Column(Float, nullable=False)
    resilience_score = Column(Float, nullable=False)
    kill_vectors = Column(JSON, nullable=True)                  # top 3 kill vectors (no business data)
    run_months = Column(Integer, nullable=False, default=24)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    opted_in = Column(Boolean, default=True)
```

---

## Step 2 — Alembic migration

`backend/alembic/versions/h9i0j1k2l3m4_benchmark_table.py`:
```python
"""add benchmark_snapshots table
Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
"""
from alembic import op
import sqlalchemy as sa

revision = 'h9i0j1k2l3m4'
down_revision = 'g8h9i0j1k2l3'


def upgrade():
    op.create_table(
        'benchmark_snapshots',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('stage', sa.String(), nullable=True),
        sa.Column('survival_rate', sa.Float(), nullable=False),
        sa.Column('median_lifespan', sa.Float(), nullable=False),
        sa.Column('resilience_score', sa.Float(), nullable=False),
        sa.Column('kill_vectors', sa.JSON(), nullable=True),
        sa.Column('run_months', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('opted_in', sa.Boolean(), server_default='true'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_benchmark_industry', 'benchmark_snapshots', ['industry'])
    op.create_index('ix_benchmark_stage', 'benchmark_snapshots', ['stage'])


def downgrade():
    op.drop_table('benchmark_snapshots')
```

---

## Step 3 — Create `backend/app/services/benchmark/` package

### `schemas.py`
```python
from pydantic import BaseModel
from typing import Optional


class BenchmarkSnapshot(BaseModel):
    industry: Optional[str] = None
    stage: Optional[str] = None
    survival_rate: float
    median_lifespan: float
    resilience_score: float
    kill_vectors: list[dict] = []


class CohortStats(BaseModel):
    industry: Optional[str]
    stage: Optional[str]
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
    industry: Optional[str]
    stage: Optional[str]
    percentile: float                 # 0–100
    sample_size: int
    label: str                        # "64th percentile vs. B2B SaaS simulations"
```

---

### `aggregator.py`
```python
from __future__ import annotations
import statistics
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.benchmark import BenchmarkSnapshot as BenchmarkModel
from app.services.benchmark.schemas import BenchmarkSnapshot, CohortStats, PercentileResult


async def snapshot_run(
    run_id: str,
    survival_rate: float,
    median_lifespan: float,
    resilience_score: float,
    kill_vectors: list[dict],
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
    q = select(BenchmarkModel).where(BenchmarkModel.opted_in == True)
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

    def pct(arr, p):
        idx = max(0, min(n - 1, int(n * p / 100)))
        return round(arr[idx], 2)

    # Aggregate kill vectors
    kv_counts: dict[str, int] = {}
    for row in rows:
        for kv in (row.kill_vectors or []):
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
    q = select(BenchmarkModel.resilience_score).where(BenchmarkModel.opted_in == True)
    if industry:
        q = q.where(BenchmarkModel.industry == industry)
    if stage:
        q = q.where(BenchmarkModel.stage == stage)
    result = await db.execute(q)
    all_scores = sorted(r[0] for r in result.all())

    n = len(all_scores)
    if n == 0:
        return PercentileResult(score=score, industry=industry, stage=stage,
                                percentile=50.0, sample_size=0,
                                label="No peer data available yet")

    rank = sum(1 for s in all_scores if s < score)
    percentile = round((rank / n) * 100, 1)

    cohort_label = f"{industry or 'all'} {stage or ''} simulations".strip()
    label = f"{percentile:.0f}th percentile vs. {cohort_label}"

    return PercentileResult(score=score, industry=industry, stage=stage,
                            percentile=percentile, sample_size=n, label=label)
```

---

## Step 4 — Auto-snapshot on run completion

In `backend/app/workers/monte_carlo.py` or wherever run completion is handled, add:

```python
# After aggregating MC results, if workspace has opted in:
from app.services.benchmark.aggregator import snapshot_run
await snapshot_run(
    run_id=run_id,
    survival_rate=mc_result["survival_rate"],
    median_lifespan=mc_result["median_lifespan"],
    resilience_score=computed_resilience_score,
    kill_vectors=mc_result.get("kill_vectors", []),
    industry=workspace.onboarding_industry,
    stage=workspace.onboarding_stage,
    db=db,
)
```

---

## Step 5 — Tests

`backend/tests/unit/benchmark/test_aggregator.py`:
```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.benchmark.aggregator import get_cohort_stats, score_percentile


def _make_mock_row(score, survival, lifespan, industry="saas", stage="seed"):
    r = MagicMock()
    r.resilience_score = score
    r.survival_rate = survival
    r.median_lifespan = lifespan
    r.industry = industry
    r.stage = stage
    r.kill_vectors = [{"type": "cash_out", "frequency": 0.4}]
    r.opted_in = True
    return r


def _mock_db_with_rows(rows):
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = rows
    result_mock.all.return_value = [(r.resilience_score,) for r in rows]
    db.execute = AsyncMock(return_value=result_mock)
    return db


def test_get_cohort_stats_returns_none_below_5_samples():
    rows = [_make_mock_row(60, 0.65, 18) for _ in range(3)]
    db = _mock_db_with_rows(rows)
    result = asyncio.get_event_loop().run_until_complete(get_cohort_stats("saas", "seed", db))
    assert result is None


def test_get_cohort_stats_returns_stats_with_5_plus_samples():
    rows = [_make_mock_row(50 + i * 5, 0.5 + i * 0.05, 15 + i) for i in range(8)]
    db = _mock_db_with_rows(rows)
    result = asyncio.get_event_loop().run_until_complete(get_cohort_stats("saas", "seed", db))
    assert result is not None
    assert result.sample_size == 8
    assert result.resilience_score_p50 > 0


def test_score_percentile_above_median():
    rows = [_make_mock_row(40 + i * 5, 0.4, 15) for i in range(10)]  # scores 40-85
    db = _mock_db_with_rows(rows)
    result = asyncio.get_event_loop().run_until_complete(score_percentile(75, "saas", "seed", db))
    assert result.percentile > 50
    assert "saas" in result.label.lower()


def test_score_percentile_no_data_returns_50():
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)
    result = asyncio.get_event_loop().run_until_complete(score_percentile(64, None, None, db))
    assert result.percentile == 50.0
    assert result.sample_size == 0


def test_cohort_stats_aggregates_kill_vectors():
    rows = [_make_mock_row(60, 0.6, 18) for _ in range(6)]
    db = _mock_db_with_rows(rows)
    result = asyncio.get_event_loop().run_until_complete(get_cohort_stats(None, None, db))
    assert "cash_out" in result.top_kill_vectors
```

---

## Verification Commands
```bash
cd backend && alembic upgrade head
cd backend && pytest tests/unit/benchmark/ -v
cd backend && ruff check app/services/benchmark/ app/models/benchmark.py
```
