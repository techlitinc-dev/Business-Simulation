# Day 20 — Expected Output

## Files Created
```
backend/app/models/benchmark.py
backend/app/services/benchmark/__init__.py
backend/app/services/benchmark/schemas.py
backend/app/services/benchmark/aggregator.py
backend/alembic/versions/h9i0j1k2l3m4_benchmark_table.py
backend/tests/unit/benchmark/__init__.py
backend/tests/unit/benchmark/test_aggregator.py
```

## Migration
```
Running upgrade g8h9i0j1k2l3 -> h9i0j1k2l3m4, add benchmark_snapshots table
```

## Sample CohortStats (50 runs, saas/seed)
```json
{
  "industry": "saas",
  "stage": "seed",
  "sample_size": 50,
  "survival_rate_p25": 0.48,
  "survival_rate_p50": 0.63,
  "survival_rate_p75": 0.78,
  "resilience_score_p25": 52.1,
  "resilience_score_p50": 64.3,
  "resilience_score_p75": 76.8,
  "median_lifespan_p50": 18.5,
  "top_kill_vectors": ["cash_out", "churn_death", "market_collapse"]
}
```

## Sample PercentileResult
```json
{
  "score": 64.0,
  "industry": "saas",
  "stage": "seed",
  "percentile": 58.0,
  "sample_size": 50,
  "label": "58th percentile vs. saas seed simulations"
}
```

## Pytest: 7 passed
