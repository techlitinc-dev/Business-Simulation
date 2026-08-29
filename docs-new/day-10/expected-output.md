# Day 10 — Expected Output

## Files Created
```
backend/app/schemas/whatif.py
backend/app/api/v1/endpoints/whatif.py
backend/tests/integration/test_whatif_api.py
```
## Files Modified
```
backend/app/api/v1/router.py      — whatif_router registered
backend/app/services/blueprint_service.py — create_version_from_override added
```

## API Responses

### POST /api/v1/whatif/sweep
```json
{
  "blueprint_id": "bp_abc",
  "param": "monthly_churn",
  "grid": [
    {"param_value": 0.02, "survival_rate": 0.9, "median_runway": 24.0, "p25_runway": 22.0, "p75_runway": 24.0},
    {"param_value": 0.07, "survival_rate": 0.55, "median_runway": 19.0, "p25_runway": 14.0, "p75_runway": 24.0},
    {"param_value": 0.12, "survival_rate": 0.15, "median_runway": 10.0, "p25_runway": 6.0, "p75_runway": 16.0}
  ]
}
```

### POST /api/v1/whatif/save-version
```json
{"blueprint_version_id": "bpv_a3f9c21b8e4d", "label": "What-If Override"}
```

### Free plan → 402
```json
{"detail": "Pro plan required for What-If Lab"}
```

## Pytest: 7 passed
