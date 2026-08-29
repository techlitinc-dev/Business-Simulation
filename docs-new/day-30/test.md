# Day 30 — Test Specification

## Test File
`backend/tests/unit/integrations/test_csv_exporter.py`

## Test Cases
1. `test_ticks_to_csv_has_header` — CSV contains "month" and "revenue" headers
2. `test_ticks_to_csv_row_count` — 2 data rows + 1 header = 3 lines
3. `test_mc_to_csv_has_survival_rate` — "survival_rate" and "0.68" in CSV
4. `test_mc_to_csv_includes_kill_vectors` — "cash_out" in CSV
5. `test_sign_payload_deterministic` — same input → same HMAC signature
6. `test_sign_payload_different_secret` — different secrets → different signatures

## Run Commands
```bash
cd backend && pytest tests/unit/integrations/ -v
cd frontend && npm run build
```

## Expected
```
6 passed
Build: 0 errors
```
