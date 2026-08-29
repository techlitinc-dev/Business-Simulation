# Day 15 — Manual Test Checklist

## Checklist

### 1. Navigate to actuals page
- [ ] URL: `/blueprints/<id>/actuals`
- [ ] "Plan vs. Actuals" page loads

### 2. Upload CSV
- [ ] Paste sample CSV into textarea
- [ ] Click "Parse Headers" → mapping step appears
- [ ] Known columns (month, revenue) are auto-mapped
- [ ] Unknown column (e.g. "notes") shows "-- skip --"
- [ ] Click "Upload Actuals" → success message

### 3. View variance report
- [ ] Navigate to variance tab
- [ ] 3 metric cards visible
- [ ] Negative deltas shown in red
- [ ] Narrative headline references real numbers from the delta

### 4. View rolling timeline
- [ ] Timeline chart shows months on X axis
- [ ] Revenue and cash lines visible
- [ ] Hovering shows tooltip

### 5. Verify drift alert fires (integration)
- [ ] Import actuals with high churn (e.g. 0.12 vs blueprint's 0.05)
- [ ] Manually run: `celery call workers.drift_monitor.check_all_blueprints`
- [ ] Check notification center — drift alert notification visible

### 6. Build check  
```bash
cd frontend && npm run build
```
- [ ] 0 errors
