# Day 06 — Manual Test Checklist

## Prerequisites
- Docker stack running: `docker compose up -d`
- Celery worker running
- A valid auth token and run_id from a completed simulation

## Checklist

### 1. Enqueue a report job
```bash
curl -X POST http://localhost:8000/api/v1/reports/deep-dive \
  -H "Authorization: Bearer <token>" \
  -H "X-Workspace-Id: <workspace_id>" \
  -H "Content-Type: application/json" \
  -d '{"run_id": "<your_run_id>"}'
```
- [ ] Response: 202
- [ ] `job_id` starts with "dr_"
- [ ] `status` is "queued"
- [ ] `total_sections` is > 0

### 2. Poll status
```bash
curl http://localhost:8000/api/v1/reports/deep-dive/<job_id>/status \
  -H "Authorization: Bearer <token>"
```
- [ ] Returns `in_progress` while running
- [ ] Returns `completed` after job finishes
- [ ] `pdf_url` is populated once complete

### 3. Download PDF
```bash
curl http://localhost:8000/api/v1/reports/deep-dive/<job_id>/download \
  -H "Authorization: Bearer <token>" \
  -o report.pdf
```
- [ ] File `report.pdf` downloaded
- [ ] File is a valid PDF (open in viewer)
- [ ] Contains cover page with workspace name

### 4. Test 404 for unknown job
```bash
curl http://localhost:8000/api/v1/reports/deep-dive/nonexistent/status \
  -H "Authorization: Bearer <token>"
```
- [ ] Returns 404

### 5. Watch WebSocket progress
```bash
# In a separate terminal, subscribe to Redis channel before enqueueing
redis-cli SUBSCRIBE "deep_report:<job_id>"
```
- [ ] See JSON messages arriving with incrementing section numbers
- [ ] Final message shows status="done"

### 6. Verify metering recorded
```bash
# Check metering table in DB or admin dashboard
# The "deep_report_generate" action should be logged for the workspace
```
- [ ] Action logged with correct workspace_id
