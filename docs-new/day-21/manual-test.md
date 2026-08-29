# Day 21 — Manual Test Checklist

## Checklist

### 1. Check percentile via curl
```bash
curl "http://localhost:8000/api/v1/benchmarks/percentile?score=64&industry=saas&stage=seed" \
  -H "Authorization: Bearer <token>"
```
- [ ] Returns JSON with `percentile` between 0 and 100
- [ ] `label` contains "saas"

### 2. Dashboard badge
- [ ] Open dashboard
- [ ] Below resilience score: "📊 Xth percentile vs. saas seed simulations" visible
- [ ] Color: green if >75th, blue if >50th, yellow if >25th, red otherwise

### 3. Report cohort chart
- [ ] Open any report
- [ ] Cohort bar chart shows 4 bars: P25, P50, P75, You
- [ ] "You" bar is highlighted in blue
- [ ] Tooltip shows values on hover

### 4. Opt-in toggle
- [ ] Settings → Workspace → benchmark opt-in checkbox
- [ ] Unchecking removes workspace from cohort calculations (verify by checking DB)

### 5. Build
```bash
cd frontend && npm run build
```
- [ ] 0 errors
