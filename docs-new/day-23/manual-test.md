# Day 23 — Manual Test Checklist

## Checklist

### 1. Create data room
```bash
curl -X POST "http://localhost:8000/api/v1/dataroom/" \
  -H "Authorization: Bearer <token>" -H "X-Workspace-Id: <ws_id>" \
  -H "Content-Type: application/json" \
  -d '{"run_id":"<run_id>","expiry_days":7,"label":"Test Room"}'
```
- [ ] Returns token and download_url

### 2. Download data room
```bash
curl "http://localhost:8000/api/v1/dataroom/<token>/download" -o room.zip
unzip room.zip -d room_contents/
ls room_contents/
```
- [ ] ZIP contains kpi_ticks.csv, mc_aggregates.json, methodology.txt
- [ ] kpi_ticks.csv has 24 rows (one per month)
- [ ] mc_aggregates.json has survival_rate field

### 3. View count increments
- [ ] Download twice
- [ ] Check Redis: `redis-cli GET "dataroom:<token>"`
- [ ] `view_count` is 2

### 4. Revoke and verify 410
```bash
curl -X DELETE "http://localhost:8000/api/v1/dataroom/<token>" \
  -H "Authorization: Bearer <token>"
curl "http://localhost:8000/api/v1/dataroom/<token>/download"
```
- [ ] DELETE returns `{"revoked": true}`
- [ ] Subsequent GET returns 410

### 5. Test lender manifest
```python
from app.services.deep_report.registry import get_manifest
manifest = get_manifest("lender_report")
print(manifest.name, len(manifest.sections))
```
- [ ] Name: "Loan Readiness Assessment"
- [ ] 8 sections

### 6. Run pytest
```bash
cd backend && pytest tests/unit/dataroom/ -v
```
- [ ] 6 passed
