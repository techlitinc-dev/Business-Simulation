# Day 28 — Manual Test Checklist

## Checklist

### 1. View decision journal for a run
```bash
curl "http://localhost:8000/api/v1/simulations/<run_id>/journal" \
  -H "Authorization: Bearer <token>"
```
- [ ] List of decisions with month, beat_ai, score fields

### 2. View workspace summary
```bash
curl "http://localhost:8000/api/v1/workspaces/journal/summary" \
  -H "Authorization: Bearer <token>" -H "X-Workspace-Id: <ws_id>"
```
- [ ] Returns beat_ai_pct and summary string

### 3. Generate a playbook
```bash
curl -X POST "http://localhost:8000/api/v1/simulations/<run_id>/playbook" \
  -H "Authorization: Bearer <token>"
```
- [ ] Returns Playbook JSON with title, steps, key_metrics_to_watch

### 4. Decision Journal UI
- [ ] Navigate to simulation → Decision Journal tab
- [ ] Summary card shows beat rate
- [ ] Each decision shows green/red badge

### 5. Run pytest
```bash
cd backend && pytest tests/unit/journal/ -v
```
- [ ] 5 passed
