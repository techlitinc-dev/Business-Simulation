# Day 04 — Expected Output

## Files Created
```
backend/app/utils/charts.py
backend/app/services/deep_report/chart_builder.py
backend/tests/unit/deep_report/test_charts.py
```

## Pytest: 10 passed

## Chart Files Generated (per run)
```
/tmp/report_charts_run_001_xxxxx/
  cash_flow.png         (≈ 45KB)
  mc_histogram.png      (≈ 32KB)
  kill_vectors.png      (≈ 28KB)
  resilience_gauge.png  (≈ 22KB)
```

## PNG Headers
All files begin with `\x89PNG\r\n\x1a\n` — valid PNG.

## Determinism Check
```python
r1 = cash_flow_curve(SAMPLE_TICKS)
r2 = cash_flow_curve(SAMPLE_TICKS)
assert r1 == r2  # True — bytes are identical
```

## Visual Description
- **cash_flow.png**: dark-background line chart, blue=cash, green=revenue, red dashed=costs, amber dotted zero line
- **mc_histogram.png**: indigo histogram of lifespan distribution, title shows survival %
- **kill_vectors.png**: horizontal bar chart with red/orange/yellow gradient bars
- **resilience_gauge.png**: polar semicircle, green/yellow/red based on score, large score number in center
