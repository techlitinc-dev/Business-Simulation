# Day 10 — Test Specification

## Test File
`backend/tests/integration/test_whatif_api.py`

## Test Cases
1. `test_sweep_requires_auth` — no auth token → 401
2. `test_sweep_returns_result` — pro user, 3 steps → 200 with 3 grid points
3. `test_save_version_creates_new_version` — 201 with new bpv_ id
4. `test_free_plan_sweep_returns_402` — free plan → 402 Payment Required
5. `test_breakeven_returns_result` — pro user → 200 with breakeven_value
6. `test_sweep_invalid_steps` — steps=1 → 422 Validation Error
7. `test_save_version_unknown_blueprint` — nonexistent blueprint_id → 404

## Run Commands
```bash
cd backend && pytest tests/integration/test_whatif_api.py -v
cd backend && ruff check app/api/v1/endpoints/whatif.py
```

## Expected
```
7 passed in <10s
```
