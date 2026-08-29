# Day 08 — Expected Output

## Files Created
```
backend/app/services/whatif/__init__.py
backend/app/services/whatif/schemas.py
backend/app/services/whatif/sweep.py
backend/app/services/whatif/breakeven.py
backend/tests/unit/whatif/__init__.py
backend/tests/unit/whatif/test_sweep.py
backend/tests/unit/whatif/test_breakeven.py
```

## Pytest: 8 passed

## Sample SweepResult (monthly_churn 2%–12%, 6 steps, 20 MC runs)
```json
{
  "blueprint_id": "bp_abc123",
  "param": "monthly_churn",
  "grid": [
    {"param_value": 0.02, "survival_rate": 0.90, "median_runway": 24.0, "p25_runway": 22.0, "p75_runway": 24.0},
    {"param_value": 0.04, "survival_rate": 0.80, "median_runway": 23.0, "p25_runway": 19.0, "p75_runway": 24.0},
    {"param_value": 0.06, "survival_rate": 0.65, "median_runway": 21.0, "p25_runway": 16.0, "p75_runway": 24.0},
    {"param_value": 0.08, "survival_rate": 0.45, "median_runway": 17.0, "p25_runway": 12.0, "p75_runway": 22.0},
    {"param_value": 0.10, "survival_rate": 0.25, "median_runway": 13.0, "p25_runway": 9.0,  "p75_runway": 19.0},
    {"param_value": 0.12, "survival_rate": 0.10, "median_runway": 9.0,  "p25_runway": 6.0,  "p75_runway": 14.0}
  ]
}
```

## Sample BreakevenResult
```json
{
  "blueprint_id": "bp_abc123",
  "param": "monthly_churn",
  "breakeven_value": 0.0631,
  "survival_at_breakeven": 0.5133,
  "message": "Your model maintains ≥50% survival only if monthly_churn stays below 0.0631"
}
```

## Performance
- 6 steps × 20 MC runs = 120 engine simulations
- Each simulation: <100ms
- Total sweep time: <12 seconds
- Break-even (20 iterations × 30 runs): <60 seconds
