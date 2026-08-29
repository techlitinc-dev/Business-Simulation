# Day 02 — Test Specification

## Test File
`backend/tests/unit/deep_report/test_data_pack.py`

---

## Test Cases

### 1. `test_tick_logs_key_present` — TICK_LOGS key resolves to a list
### 2. `test_mc_aggregates_key_present` — MC_AGGREGATES returns stored run.mc_result dict
### 3. `test_run_metadata_structure` — run_metadata dict contains run_id and seed
### 4. `test_engine_config_returned` — engine_config contains months field
### 5. `test_chronicle_extracted` — chronicle is a dict from state_snapshot
### 6. `test_only_requested_keys_in_pack` — pack only has keys declared in section.data_inputs
### 7. `test_pack_is_serializable` — json.dumps(pack) succeeds without error
### 8. `test_no_warnings_when_complete` — validate_data_pack returns [] when all keys have values
### 9. `test_warning_when_key_is_none` — validate_data_pack returns warning for None keys
### 10. `test_deterministic_same_inputs_same_output` — calling twice with same inputs returns identical dict

## Run Commands

```bash
cd backend && pytest tests/unit/deep_report/ -v
cd backend && ruff check app/services/deep_report/data_pack.py
cd backend && mypy app/services/deep_report/data_pack.py --ignore-missing-imports
```

## Expected Pass Output
```
10 passed in <2s
```
