# Day 21 — Test Specification

## Test Files
- `backend/tests/integration/test_benchmark_api.py`
- Frontend: build + lint

## Test Cases
1. `test_get_percentile_returns_result` — GET /benchmarks/percentile?score=64 → 200 with 0≤percentile≤100
2. `test_get_cohort_returns_none_when_insufficient` — unknown industry → 200 null
3. `test_benchmark_badge_renders_with_data` — BenchmarkBadge shows "Xth percentile" text
4. `test_benchmark_badge_hidden_when_sample_too_small` — sample_size<5 → badge not rendered
5. `test_cohort_chart_renders_4_bars` — P25/P50/P75/You bars visible

## Run Commands
```bash
cd backend && pytest tests/integration/test_benchmark_api.py -v
cd frontend && npm run build
```

## Expected
```
Tests: 2 integration passing
Build: 0 errors
```
