"""Unit tests for the benchmark aggregator (Day 18)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.services.benchmark.aggregator import get_cohort_stats, score_percentile


def _make_mock_row(
    score: float, survival: float, lifespan: float, industry: str = "saas", stage: str = "seed"
) -> MagicMock:
    r = MagicMock()
    r.resilience_score = score
    r.survival_rate = survival
    r.median_lifespan = lifespan
    r.industry = industry
    r.stage = stage
    r.kill_vectors = [{"type": "cash_out", "frequency": 0.4}]
    r.opted_in = True
    return r


def _mock_db_with_rows(rows: list[MagicMock]) -> AsyncMock:
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = rows
    result_mock.all.return_value = [(r.resilience_score,) for r in rows]
    db.execute = AsyncMock(return_value=result_mock)
    return db


async def test_get_cohort_stats_returns_none_below_5_samples() -> None:
    rows = [_make_mock_row(60, 0.65, 18) for _ in range(3)]
    db = _mock_db_with_rows(rows)
    result = await get_cohort_stats("saas", "seed", db)
    assert result is None


async def test_get_cohort_stats_returns_stats_with_5_plus_samples() -> None:
    rows = [_make_mock_row(50 + i * 5, 0.5 + i * 0.05, 15 + i) for i in range(8)]
    db = _mock_db_with_rows(rows)
    result = await get_cohort_stats("saas", "seed", db)
    assert result is not None
    assert result.sample_size == 8
    assert result.resilience_score_p50 > 0


async def test_score_percentile_above_median() -> None:
    rows = [_make_mock_row(40 + i * 5, 0.4, 15) for i in range(10)]  # scores 40-85
    db = _mock_db_with_rows(rows)
    result = await score_percentile(75, "saas", "seed", db)
    assert result.percentile > 50
    assert "saas" in result.label.lower()


async def test_score_percentile_no_data_returns_50() -> None:
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)
    result = await score_percentile(64, None, None, db)
    assert result.percentile == 50.0
    assert result.sample_size == 0


async def test_cohort_stats_aggregates_kill_vectors() -> None:
    rows = [_make_mock_row(60, 0.6, 18) for _ in range(6)]
    db = _mock_db_with_rows(rows)
    result = await get_cohort_stats(None, None, db)
    assert result is not None
    assert "cash_out" in result.top_kill_vectors
