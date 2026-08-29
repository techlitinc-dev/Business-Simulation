# Day 11 — Manual Test Checklist

## Checklist

### 1. Navigate to What-If Lab
- [ ] URL: `/blueprints/<id>/whatif`
- [ ] Page loads without error

### 2. Free plan paywall
- [ ] Log in as free plan → paywall card visible, no sweep controls

### 3. Pro plan sweep
- [ ] Select "Monthly Churn" from dropdown
- [ ] Click "Run Sweep"
- [ ] Button shows "Running sweeps…" during fetch
- [ ] Heatmap appears with 8 color-coded cells
- [ ] Colors: left cells green (low churn = high survival), right cells red

### 4. Break-even card
- [ ] Amber card appears below heatmap
- [ ] Shows exact breakeven threshold value
- [ ] Message is readable plain English

### 5. Save as version
- [ ] Click one of the grid point buttons
- [ ] Success message appears: "✅ Saved as version: bpv_xxx"
- [ ] Navigate to blueprint page → new version visible in version list

### 6. Different parameter
- [ ] Switch dropdown to "Customer Acquisition Cost"
- [ ] Range updates to new min/max
- [ ] Run sweep → heatmap shows different pattern

### 7. Frontend build
```bash
cd frontend && npm run build
```
- [ ] 0 errors
