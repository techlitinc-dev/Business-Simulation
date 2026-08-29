# Day 01 — Manual Test Checklist

## Prerequisites
- Docker stack running: `docker compose up -d`
- Redis accessible
- Celery worker running: `cd backend && celery -A app.core.celery_app worker --loglevel=info`

---

## Checklist

### 1. Verify package import
- [ ] Open a Python shell inside the backend container or venv
- [ ] Run: `from app.services.deep_report.registry import get_manifest, FULL_MANIFEST`
- [ ] Expected: No import error

### 2. Verify manifest section count in shell
```python
from app.services.deep_report.registry import FULL_MANIFEST
from app.services.deep_report.manifest import ReportTier

print(len(FULL_MANIFEST.sections))           # → 21
print(FULL_MANIFEST.total_page_budget)       # → 70

free = FULL_MANIFEST.sections_for_tier(ReportTier.FREE)
print([s.section_number for s in free])      # → [2, 9, 11]

pro = FULL_MANIFEST.sections_for_tier(ReportTier.PRO)
print(len(pro))                              # → 13

ent = FULL_MANIFEST.sections_for_tier(ReportTier.ENTERPRISE)
print(len(ent))                              # → 21
```
- [ ] All outputs match expected values above

### 3. Enqueue a Celery job manually
```python
from app.workers.report_job import generate_deep_report
result = generate_deep_report.delay(
    job_id="manual-test-001",
    run_id="any-run-id",
    report_type="resilience_audit",
    tier="enterprise"
)
print(result.id)   # Celery task ID
```
- [ ] No exception raised
- [ ] Celery worker terminal shows 21 log lines (one per section)

### 4. Verify Redis progress key is written
```bash
redis-cli GET "deep_report:progress:manual-test-001"
```
- [ ] Returns a JSON string with `"section": 21, "status": "done"`

### 5. Verify Redis pub/sub messages
```bash
redis-cli SUBSCRIBE "deep_report:manual-test-001"
# (open before enqueueing)
```
- [ ] See multiple JSON messages arriving, each with incrementing `"section"` field
- [ ] First message: `"status": "writing"`, `"section": 1`
- [ ] Final message: `"status": "done"`, `"section": 21`

### 6. Confirm Free tier job only processes 3 sections
```python
result = generate_deep_report.delay(
    job_id="manual-test-free",
    run_id="any-run-id",
    report_type="resilience_audit",
    tier="free"
)
```
- [ ] Celery worker shows only 3 log lines
- [ ] Redis progress key shows `"total": 3`

### 7. Confirm invalid report_type raises KeyError
```python
from app.services.deep_report.registry import get_manifest
try:
    get_manifest("invalid_type")
except KeyError as e:
    print("KeyError raised:", e)
```
- [ ] `KeyError` is raised and printed

### 8. Verify task return value
```python
result = generate_deep_report.delay(
    job_id="manual-test-return",
    run_id="any-run-id",
    report_type="resilience_audit",
    tier="pro"
)
import time; time.sleep(2)
print(result.result)
```
- [ ] Returns dict with `"sections_completed": 13`, `"status": "stub_complete"`

### 9. Run full pytest suite — no regressions
```bash
cd backend && pytest --tb=short -q
```
- [ ] All existing tests still pass
- [ ] 12 new tests pass
- [ ] Zero failures, zero errors

### 10. Lint check
```bash
cd backend && ruff check app/services/deep_report/ app/workers/report_job.py
```
- [ ] Output: `All checks passed!`

---

## Sign-Off Criteria

All boxes above must be checked before moving to Day 02.
The key deliverable is: **a Celery job that walks the full 21-section manifest, publishes progress to Redis, and completes without error — content is stub text.**
