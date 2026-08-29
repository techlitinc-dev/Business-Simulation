# Day 13 — Test Specification

## Test File
`backend/tests/unit/actuals/test_variance.py`

## Test Cases
1. `test_compute_variance_with_actuals` — returns VarianceDelta, survival_delta ≤ 0 when churn increased
2. `test_compute_variance_no_actuals_raises` — raises ValueError "No actuals"
3. `test_variance_delta_fields_are_numeric` — all delta fields are float
4. `test_narrator_with_mock_provider_returns_narrative` — narrate_variance returns VarianceNarrativeOutput with headline
5. `test_narrator_headline_contains_percentage` — headline references survival rate numbers

## Run Commands
```bash
cd backend && pytest tests/unit/actuals/ -v
```

## Expected
```
All actuals tests passing (8 from Day 12 + 5 new = 13 total)
```
