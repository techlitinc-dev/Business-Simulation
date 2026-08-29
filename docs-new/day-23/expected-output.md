# Day 23 — Expected Output

## Files Created
```
backend/app/services/deep_report/manifests/__init__.py
backend/app/services/deep_report/manifests/lender_manifest.py
backend/app/services/dataroom/__init__.py
backend/app/services/dataroom/schemas.py
backend/app/services/dataroom/dataroom_service.py
backend/app/api/v1/endpoints/dataroom.py
backend/tests/unit/dataroom/__init__.py
backend/tests/unit/dataroom/test_dataroom_service.py
```

## Data Room Bundle Contents (ZIP)
```
data_room_a3f9c21b.zip
  simulation_audit.pdf    (the deep-dive report PDF if generated)
  kpi_ticks.csv          (all 24 months of KPI data)
  mc_aggregates.json     (Monte Carlo results)
  methodology.txt        (plain-text methodology note)
```

## API Responses

### POST /api/v1/dataroom/
```json
{
  "token": "a3f9c21b8e4d",
  "download_url": "/api/v1/dataroom/a3f9c21b8e4d/download",
  "expires_at": "2026-08-26T07:00:00",
  "label": "Investor Data Room"
}
```

### GET /api/v1/dataroom/a3f9c21b8e4d/download
```
HTTP 200
Content-Type: application/zip
Content-Disposition: attachment; filename="data_room_a3f9c21b8e4d.zip"
```

### After revoke — GET /download
```
HTTP 410 Gone: Data room link has expired or been revoked
```

## Pytest: 6 passed
