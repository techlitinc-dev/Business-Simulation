# Day 08 — Test Specification

## Test Files
- `backend/tests/unit/whatif/__init__.py`
- `backend/tests/unit/whatif/test_sweep.py`
- `backend/tests/unit/whatif/test_breakeven.py`

## Test Cases

### Sweep Tests
1. `test_patch_payload_flat` — overrides top-level key, original dict unchanged
2. `test_patch_payload_nested` — dot-notation `financials.monthly_churn` correctly patches nested key
3. `test_sweep_grid_has_correct_length` — steps=6 → 6 SweepGridPoints in result
4. `test_sweep_survival_rates_monotonic` — higher churn = lower survival (at least 3 of 4 pairs decrease)
5. `test_sweep_result_serializable` — result.model_dump() is JSON-serializable

### Break-Even Tests
6. `test_breakeven_returns_result` — returns BreakevenResult with breakeven_value in [search_min, search_max]
7. `test_breakeven_message_contains_param_name` — message string contains the param name
8. `test_breakeven_survival_in_range` — survival_at_breakeven is between 0.0 and 1.0

## Run Commands
```bash
cd backend && pytest tests/unit/whatif/ -v
cd backend && ruff check app/services/whatif/
```

## Expected
```
8 passed in <3s
```
