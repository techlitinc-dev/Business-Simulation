# Day 32 — Manual Test Checklist

## Checklist

### 1. Model routing via env
```bash
# Set in .env:
DEEPSEEK_MODEL_EXECUTIVE_SUMMARY=deepseek-reasoner
```
```python
from app.agents.llm.router import get_model_for_task
print(get_model_for_task("executive_summary"))   # deepseek-reasoner
print(get_model_for_task("generic_narrative"))   # deepseek-chat (default)
```
- [ ] executive_summary returns the env-configured model
- [ ] Unknown task falls back to LLM_MODEL

### 2. Cost guard — simulate budget exceeded
```python
from app.services.cost_guard import record_usage, check_monthly_budget
from unittest.mock import patch
with patch("app.services.cost_guard._get_redis") as mock_redis:
    r = mock_redis.return_value
    r.get.return_value = "2000001"
    try:
        check_monthly_budget("ws_001")
        print("No error — FAIL")
    except Exception as e:
        print(f"Correctly raised: {e.status_code}")
```
- [ ] Raises 429

### 3. Generate report in Spanish
```bash
curl -X POST "http://localhost:8000/api/v1/reports/deep-dive" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"run_id":"<id>","lang":"es"}'
```
- [ ] PDF sections written in Spanish
- [ ] Numbers/percentages still formatted correctly

### 4. Check achievements
```bash
curl "http://localhost:8000/api/v1/gamification/achievements" \
  -H "Authorization: Bearer <token>" -H "X-Workspace-Id: <ws_id>"
```
- [ ] Returns array of earned achievements
- [ ] "Simulation Pioneer" achievement appears after first run

### 5. Generate certification PDF
```bash
curl -X POST "http://localhost:8000/api/v1/gamification/certification/<run_id>" \
  -H "Authorization: Bearer <token>" -o certification.pdf
```
- [ ] certification.pdf downloaded
- [ ] Opens with workspace name, score, percentile, criteria checkmarks

### 6. Frontend gamification
- [ ] After completing a run with score ≥90th percentile, achievement toast pops
- [ ] "🏆 Forge-Validated Business" badge visible on dashboard
- [ ] Click badge → download certification PDF

### 7. Final full test suite
```bash
cd backend && pytest --tb=short -q
```
- [ ] All tests pass (previous + new)
- [ ] 0 failures

### 8. Final frontend build
```bash
cd frontend && npm run build && npm run lint
```
- [ ] 0 errors
- [ ] 0 lint warnings

---

## Sign-Off: All 32 Days Complete

Verify the full docs-new structure:
```bash
ls docs-new/ | wc -l   # should be 32
ls docs-new/day-01/    # instructions.md, test.md, expected-output.md, manual-test.md
ls docs-new/day-32/    # same 4 files
```
- [ ] 32 directories
- [ ] Each has exactly 4 files
