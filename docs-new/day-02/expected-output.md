# Day 02 — Expected Output

## Files Modified/Created
- `backend/app/services/deep_report/data_pack.py` — fully implemented (replaces stub)

## Pytest
```
10 passed in <2s
```

## Sample Data Pack for Section 2 (Executive Summary) Against a Real Run

```json
{
  "tick_logs": [
    {"month": 1, "revenue": 12000, "costs": 18000, "cash": 94000, "customers": 8, "mrr": 12000, "runway_months": 5.2, "ltv_cac_ratio": 1.1, "churn_rate": 0.05},
    {"month": 2, "revenue": 15500, "costs": 18200, "cash": 91300, "customers": 11, "mrr": 15500, "runway_months": 5.0, "ltv_cac_ratio": 1.3, "churn_rate": 0.04}
  ],
  "mc_aggregates": {
    "survival_rate": 0.68,
    "median_lifespan": 17,
    "kill_vectors": [{"type": "cash_out", "frequency": 0.41}, {"type": "churn_death", "frequency": 0.27}]
  },
  "forge_vulnerabilities": [
    {"title": "High CAC relative to LTV", "severity": "HIGH", "description": "..."}
  ]
}
```

## Validation Warnings (when MC not available)

```python
validate_data_pack(pack, section)
# → ["DataInputKey.MC_AGGREGATES resolved to None for section 2"]
```

## Key Property: Determinism
Calling `build_data_pack(section, same_run_id, db)` twice returns byte-for-byte identical dicts.
