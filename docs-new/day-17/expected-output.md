# Day 17 — Expected Output

## Files Created
```
backend/app/api/v1/endpoints/advisory.py
frontend/src/features/advisory/api.ts
frontend/src/features/advisory/PersonaCard.tsx
frontend/src/features/advisory/AdvisoryBoardPanel.tsx
```

## UI
- "Get Advisory Board Review" button (purple)
- While loading: button shows "Running Board Review…"
- On complete: 2×2 grid of persona cards with colored borders (blue=CFO, green=CMO, red=Risk, amber=Operator)
- Summary card below: consensus verdict, agreements (green), conflicts (orange), priority action (blue box)

## API
- POST → 202 `{"job_id": "adv_xxx", "status": "queued"}`
- GET (complete) → `{"status": "complete", "result": {...reviews, summary...}}`

## Build: 0 errors
