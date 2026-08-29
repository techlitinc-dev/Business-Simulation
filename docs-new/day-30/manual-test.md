# Day 30 — Manual Test Checklist

## Checklist

### 1. Export ticks CSV
```bash
curl "http://localhost:8000/api/v1/export/runs/<run_id>/ticks.csv" \
  -H "Authorization: Bearer <token>" -o ticks.csv
```
- [ ] File `ticks.csv` downloaded
- [ ] 25 lines (header + 24 months)
- [ ] All columns present: month, revenue, costs, cash

### 2. Export MC CSV
```bash
curl "http://localhost:8000/api/v1/export/runs/<run_id>/mc.csv" \
  -H "Authorization: Bearer <token>" -o mc.csv
```
- [ ] `mc.csv` has survival_rate, median_lifespan rows
- [ ] Kill vectors section present

### 3. Test webhook signature
```python
from app.services.integrations.webhook_service import _sign_payload
payload = {"run_id": "test", "event": "run.completed"}
sig = _sign_payload(payload, "my-secret")
print(sig)  # deterministic sha256 hex
```
- [ ] Same output each time for same input

### 4. Test Slack notification (mock)
```python
import asyncio
from app.services.integrations.slack_notifier import notify_run_complete
asyncio.run(notify_run_complete("https://hooks.slack.com/invalid", "run_001", 0.68, 64.0))
```
- [ ] Warning logged (not an exception) because URL is invalid

### 5. Integrations settings page
- [ ] Navigate to Settings → Integrations
- [ ] Slack URL input visible
- [ ] Save adds webhook to list

### 6. Run pytest
```bash
cd backend && pytest tests/unit/integrations/ -v
```
- [ ] 6 passed
