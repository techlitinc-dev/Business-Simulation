# Day 06 — Expected Output

## Files Created
```
backend/app/schemas/deep_report.py
backend/app/api/v1/endpoints/deep_report.py
backend/tests/integration/test_deep_report_api.py
```

## Files Modified
```
backend/app/api/v1/router.py     — deep_report router registered
backend/app/workers/report_job.py — saves PDF after section loop
backend/app/core/config.py        — REPORT_STORAGE_DIR added
```

## API Response Examples

### POST /api/v1/reports/deep-dive
```json
{
  "job_id": "dr_a3f9c21b8e4d",
  "run_id": "run_abc123",
  "status": "queued",
  "tier": "pro",
  "total_sections": 13,
  "pdf_url": null
}
```

### GET /api/v1/reports/deep-dive/dr_a3f9c21b8e4d/status (in progress)
```json
{
  "job_id": "dr_a3f9c21b8e4d",
  "run_id": "run_abc123",
  "status": "in_progress",
  "tier": "pro",
  "total_sections": 13,
  "pdf_url": null
}
```

### GET /api/v1/reports/deep-dive/dr_a3f9c21b8e4d/status (completed)
```json
{
  "job_id": "dr_a3f9c21b8e4d",
  "run_id": "run_abc123",
  "status": "completed",
  "tier": "pro",
  "total_sections": 13,
  "pdf_url": "/api/v1/reports/deep-dive/dr_a3f9c21b8e4d/download"
}
```

### GET /api/v1/reports/deep-dive/dr_a3f9c21b8e4d/download
```
HTTP 200
Content-Type: application/pdf
Content-Disposition: attachment; filename="report_dr_a3f9c21b8e4d.pdf"
Body: <binary PDF bytes>
```

## WebSocket Progress Events
Channel: `deep_report:dr_a3f9c21b8e4d`
```json
{"job_id": "dr_a3f9c21b8e4d", "section": 1, "total": 13, "status": "writing", "section_title": "Cover, Disclaimer, Table of Contents"}
{"job_id": "dr_a3f9c21b8e4d", "section": 1, "total": 13, "status": "done", "section_title": "Cover, Disclaimer, Table of Contents"}
...
{"job_id": "dr_a3f9c21b8e4d", "section": 13, "total": 13, "status": "done", "section_title": "Counter-Factual Analysis"}
```

## Pytest: 8 passed
