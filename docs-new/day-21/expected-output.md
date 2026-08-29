# Day 21 — Expected Output

## Files Created
```
backend/app/api/v1/endpoints/benchmark.py
frontend/src/features/benchmark/api.ts
frontend/src/features/benchmark/BenchmarkBadge.tsx
frontend/src/features/benchmark/CohortChart.tsx
```

## Files Modified
```
frontend/src/features/dashboard/ResilienceGauge.tsx  — BenchmarkBadge added below score
frontend/src/features/reports/ReportPage.tsx          — CohortChart added
frontend/src/features/settings/WorkspaceSettingsPage.tsx — opt-in toggle
backend/app/api/v1/router.py                          — benchmark_router registered
```

## UI
- Dashboard resilience gauge now shows: "📊 58th percentile vs. saas seed simulations"
- Report page includes bar chart: P25/P50/P75/You bars on dark background
- "You" bar in blue, peer bars in slate
- Settings: opt-in checkbox

## API
- GET /benchmarks/percentile?score=64&industry=saas → PercentileResult JSON
- GET /benchmarks/cohort?industry=saas&stage=seed → CohortStats JSON or null

## Build: 0 errors
