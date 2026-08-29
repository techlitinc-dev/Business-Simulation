# Day 18 — Test Specification

## Test File
`backend/tests/unit/copilot/test_copilot_service.py`

## Test Cases
1. `test_number_pattern_extracts_large_numbers` — regex finds 125000 and 86000
2. `test_chat_returns_required_keys` — result has answer, grounded, flagged_claims
3. `test_chat_grounded_when_no_suspicious_numbers` — numbers ≤100 not flagged → grounded=True
4. `test_chat_flagged_when_hallucinated_number` — number >100 not in context → grounded=False, flagged_claims non-empty
5. `test_chat_endpoint_returns_200` — POST /simulations/{run_id}/chat returns 200

## Run Commands
```bash
cd backend && pytest tests/unit/copilot/ -v
```

## Expected
```
5 passed in <3s
```
