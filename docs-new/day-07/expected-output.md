# Day 07 — Expected Output

## Files Created
```
frontend/src/features/reports/deep_report/
  api.ts
  DeepReportPage.tsx
  SectionProgressFeed.tsx
  ReportViewer.tsx
```

## Files Modified
```
frontend/src/features/reports/ReportPage.tsx  — added "Deep-Dive Report" tab
backend/app/api/v1/endpoints/ws.py            — added /ws/reports/{job_id} route
```

## Build Output
```
vite build
✓ 0 errors, 0 warnings
dist/assets/index-[hash].js
```

## UI Behaviour

### Free Plan User
- Sees paywall card with "Upgrade to Pro" CTA
- No generate button visible

### Pro Plan User — Idle State
- "Generate Deep-Dive Report" button visible
- Tier and section count shown in subtitle

### Generating State
- Progress bar fills left to right as sections complete
- Section list appears below: green checkmark for done, spinning icon for current
- Text: "Writing section 7 of 13: Counter-Factual Analysis"

### Complete State
- "✅ Report ready — 13 sections generated"
- "⬇️ Download PDF" button
- Embedded PDF iframe (70vh height) showing the rendered report

## WebSocket Message Flow (browser DevTools → Network → WS)
```
← {"job_id": "dr_abc", "section": 1, "total": 13, "status": "writing", "section_title": "Cover..."}
← {"job_id": "dr_abc", "section": 1, "total": 13, "status": "done", "section_title": "Cover..."}
← {"job_id": "dr_abc", "section": 2, "total": 13, "status": "writing", "section_title": "Executive Summary"}
...
```
