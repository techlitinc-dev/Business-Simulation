# Day 20 — Test Specification

## Test File
`backend/tests/unit/benchmark/test_aggregator.py`

## Test Cases
1. `test_get_cohort_stats_returns_none_below_5_samples` — <5 rows → None
2. `test_get_cohort_stats_returns_stats_with_5_plus_samples` — ≥5 rows → CohortStats with sample_size=8
3. `test_score_percentile_above_median` — score 75 in [40..85] → percentile >50
4. `test_score_percentile_no_data_returns_50` — empty DB → percentile=50.0, sample_size=0
5. `test_cohort_stats_aggregates_kill_vectors` — kill_vectors aggregated, "cash_out" in top_kill_vectors
6. `test_snapshot_run_persists_record` — snapshot_run adds row to DB with correct fields
7. `test_score_percentile_label_contains_industry` — label includes "saas"

## Run Commands
```bash
cd backend && pytest tests/unit/benchmark/ -v
cd backend && alembic upgrade head
```

## Expected
```
7 passed
Migration clean
```
