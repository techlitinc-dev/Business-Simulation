# Day 11 — Expected Output

## Files Created
```
frontend/src/features/whatif/api.ts
frontend/src/features/whatif/WhatIfLabPage.tsx
frontend/src/features/whatif/SweepHeatmap.tsx
frontend/src/features/whatif/BreakevenCard.tsx
```

## UI Flow

### Free Plan
- Paywall card with 🔬 icon, upgrade button

### Pro Plan — Idle
- Parameter dropdown (Monthly Churn, CAC, Price, Fixed Costs)
- Range display and "Run Sweep" button

### Pro Plan — Results
- Color-coded heatmap grid (green → red) with % labels and param values below
- Break-even amber card: "Your model maintains ≥50% survival only if monthly_churn stays below 0.0631"
- Row of grid point buttons — click any to save as new blueprint version
- Success message: "✅ Saved as version: bpv_xxx"

## Build: 0 errors, 0 lint warnings
