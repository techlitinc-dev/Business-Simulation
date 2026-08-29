# Day 06 — Test Specification

## Test File
`backend/tests/integration/test_deep_report_api.py`

## Test Cases

### 1. `test_request_deep_report_queued` — POST /reports/deep-dive returns 202 with job_id starting "dr_" and status="queued"
### 2. `test_get_report_status_404_for_unknown_job` — GET status for unknown job_id returns 404
### 3. `test_download_404_before_completion` — GET download for nonexistent job returns 404
### 4. `test_report_requires_auth` — POST without auth headers returns 401
### 5. `test_free_tier_gets_3_sections` — free plan workspace → total_sections=3
### 6. `test_pro_tier_gets_13_sections` — pro plan workspace → total_sections=13
### 7. `test_job_status_in_progress_after_enqueue` — immediately after enqueue, status=queued or in_progress
### 8. `test_invalid_report_type_returns_422` — unknown report_type returns 422

## Run Commands
```bash
cd backend && pytest tests/integration/test_deep_report_api.py -v
cd backend && ruff check app/api/v1/endpoints/deep_report.py
```

## Expected
```
8 passed in <5s
```
