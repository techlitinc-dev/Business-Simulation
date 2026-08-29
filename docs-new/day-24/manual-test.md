# Day 24 — Manual Test Checklist

## Checklist

### 1. Navigate to Report page → Investor Toolkit tab
- [ ] Tab visible
- [ ] 2 action cards shown (Investment Teaser, Pitch Deck Outline)

### 2. Generate Investment Teaser
- [ ] Click "Generate Investment Teaser"
- [ ] Button shows "Generating…"
- [ ] PDF downloads automatically: `teaser_<run_id>.pdf`
- [ ] PDF has 1 page with Problem, Solution, Metrics, Ask

### 3. Generate Pitch Deck
- [ ] Click "Generate Pitch Deck Outline"
- [ ] PDF downloads with 10-12 slides listed

### 4. Create Data Room
- [ ] Click "🔗 Create Data Room Link"
- [ ] Room card appears with token, expiry date
- [ ] Click "Copy Link" → opens /api/v1/dataroom/<token>/download in new tab
- [ ] ZIP downloads

### 5. Revoke Data Room
- [ ] Click "Revoke" on a room card
- [ ] Card disappears from list
- [ ] Verify link returns 410: `curl <download_url>`

### 6. Build
```bash
cd frontend && npm run build
```
- [ ] 0 errors
