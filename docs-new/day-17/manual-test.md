# Day 17 — Manual Test Checklist

## Checklist

### 1. Request board review via curl
```bash
curl -X POST "http://localhost:8000/api/v1/advisory/blueprints/<bp_id>/board-review" \
  -H "Authorization: Bearer <token>" -H "X-Workspace-Id: <ws_id>"
```
- [ ] 202 response with job_id starting "adv_"

### 2. Poll for result
```bash
curl "http://localhost:8000/api/v1/advisory/board-review/<job_id>" \
  -H "Authorization: Bearer <token>"
```
- [ ] Returns `{"status": "complete", "result": {...}}`
- [ ] 4 reviews in result.reviews
- [ ] Summary has consensus_verdict

### 3. Open Advisory Board tab in browser (Blueprint detail page)
- [ ] "Get Advisory Board Review" button visible
- [ ] Click button → loading state
- [ ] After ~5s: 4 persona cards render
- [ ] CFO card has blue border, CMO green, Risk red, Operator amber
- [ ] Summary section shows agreements and priority action

### 4. Build check
```bash
cd frontend && npm run build
```
- [ ] 0 errors
