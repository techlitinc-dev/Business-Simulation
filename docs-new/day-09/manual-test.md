# Day 09 — Manual Test Checklist

## Checklist

### 1. Render charts from a sweep result
```python
from app.services.whatif.schemas import SweepResult, SweepGridPoint
from app.services.whatif.visualizer import render_sweep_charts

mock_sweep = SweepResult(
    blueprint_id="bp_test",
    param="monthly_churn",
    grid=[
        SweepGridPoint(param_value=0.02, survival_rate=0.90, median_runway=24, p25_runway=22, p75_runway=24),
        SweepGridPoint(param_value=0.05, survival_rate=0.65, median_runway=20, p25_runway=16, p75_runway=24),
        SweepGridPoint(param_value=0.08, survival_rate=0.40, median_runway=15, p25_runway=10, p75_runway=20),
        SweepGridPoint(param_value=0.11, survival_rate=0.15, median_runway=10, p25_runway=6,  p75_runway=16),
    ]
)
bundle = render_sweep_charts(mock_sweep, "/tmp/whatif_charts")
print(list(bundle.charts.keys()))
```
- [ ] 3 keys: heatmap, survival_line, tornado
- [ ] All 3 PNG files exist at /tmp/whatif_charts/

### 2. Open charts visually
- [ ] heatmap.png: colored 1-row grid, green on left (low churn), red on right (high churn)
- [ ] survival_line.png: declining blue line, shaded band, yellow 50% threshold
- [ ] tornado.png: single horizontal bar

### 3. Verify determinism
```python
r1 = render_sweep_charts(mock_sweep, "/tmp/test1")
r2 = render_sweep_charts(mock_sweep, "/tmp/test2")
with open("/tmp/test1/heatmap.png", "rb") as f: b1 = f.read()
with open("/tmp/test2/heatmap.png", "rb") as f: b2 = f.read()
assert b1 == b2
```
- [ ] Bytes are identical

### 4. Run full pytest
```bash
cd backend && pytest tests/unit/whatif/ -v
```
- [ ] 14 passing
