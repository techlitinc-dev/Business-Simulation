# Day 15 — Expected Output

## Files Created
```
backend/app/api/v1/endpoints/actuals.py
frontend/src/features/actuals/api.ts
frontend/src/features/actuals/ActualsUploadPage.tsx
frontend/src/features/actuals/VarianceReportPage.tsx
frontend/src/features/actuals/RollingForecastTimeline.tsx
```

## UI Flow

### Step 1 — Paste CSV
- Textarea for CSV input
- "Parse Headers" button

### Step 2 — Column Mapping
- Each CSV header shows a dropdown → mapped field
- Auto-maps: "month" → month, "revenue" → revenue, etc.
- Unknown columns: dropdown shows "-- skip --"
- "Upload Actuals" button

### Step 3 — Done
- "✅ Upload complete — 3 created · 0 updated"

### Variance Report
- 3 metric cards: Resilience Score (−14.3 pts), Survival Rate (−14pp), Median Runway (−5mo)
- Red text on negative deltas
- Narrative card: headline + explanation paragraphs + outlook line

### Rolling Timeline
- Green line = revenue over months
- Blue line = cash over months
- Dark-theme Recharts chart

## Build: 0 errors
