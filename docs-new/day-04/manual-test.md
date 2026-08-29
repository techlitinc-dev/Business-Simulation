# Day 04 — Manual Test Checklist

## Checklist

### 1. Generate charts from the Python shell
```python
from app.utils.charts import cash_flow_curve, mc_distribution_histogram
ticks = [{"month": i, "cash": 100000 - i*3000, "revenue": 10000+i*500, "costs": 12000} for i in range(1, 13)]
mc = {"survival_rate": 0.68, "lifespan_distribution": list(range(6,25)), "kill_vectors": [{"type": "cash_out", "frequency": 0.4}]}
png = cash_flow_curve(ticks)
open("/tmp/test_cash.png", "wb").write(png)
```
- [ ] No matplotlib display window pops up (headless Agg backend)
- [ ] `/tmp/test_cash.png` exists and is a valid PNG (open in image viewer)
- [ ] Chart has dark background, 3 lines (cash, revenue, costs)

### 2. Test render_charts_for_run
```python
from app.services.deep_report.chart_builder import render_charts_for_run
bundle = render_charts_for_run(ticks, mc, "manual-test-run")
print(bundle.charts.keys())
# dict_keys(['cash_flow', 'mc_histogram', 'kill_vectors', 'resilience_gauge'])
```
- [ ] 4 keys in charts dict
- [ ] All 4 files exist on disk

### 3. Verify determinism
- [ ] Call `cash_flow_curve(ticks)` twice
- [ ] `r1 == r2` is True

### 4. Verify empty data doesn't crash
```python
from app.utils.charts import kill_vector_bar
result = kill_vector_bar({})
assert len(result) > 0
```
- [ ] No exception

### 5. Open PNGs visually
- [ ] Open `cash_flow.png` — dark theme, lines visible
- [ ] Open `mc_histogram.png` — histogram bars visible
- [ ] Open `kill_vectors.png` — horizontal bars visible
- [ ] Open `resilience_gauge.png` — semicircle gauge visible

### 6. Run pytest
```bash
cd backend && pytest tests/unit/deep_report/test_charts.py -v
```
- [ ] 10 passed
