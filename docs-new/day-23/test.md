# Day 23 — Test Specification

## Test File
`backend/tests/unit/dataroom/test_dataroom_service.py`

## Test Cases
1. `test_create_and_retrieve_dataroom` — create_dataroom returns token and download_url
2. `test_revoke_deletes_key` — revoke_dataroom calls redis.delete
3. `test_record_view_increments_count` — view_count increments on each call
4. `test_get_dataroom_returns_none_for_expired` — expired entry returns None
5. `test_lender_manifest_registered` — get_manifest("lender_report") returns LENDER_MANIFEST
6. `test_lender_manifest_has_8_sections` — 8 sections with page budget ~29

## Run Commands
```bash
cd backend && pytest tests/unit/dataroom/ -v
cd backend && ruff check app/services/dataroom/
```

## Expected
```
6 passed
```
