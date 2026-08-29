# Day 12 — Test Specification

## Test File
`backend/tests/unit/actuals/test_importer.py`

## Test Cases
1. `test_parse_csv_basic` — 3 rows parsed, month and revenue fields mapped correctly
2. `test_parse_csv_with_column_mapping` — custom mapping "Monthly Revenue"→"revenue" applied
3. `test_validate_row_valid` — clean row returns empty errors list
4. `test_validate_row_missing_month` — missing month field returns error containing "month"
5. `test_validate_row_invalid_number` — non-numeric revenue returns error containing "revenue"
6. `test_import_actuals_created_count` — 2 valid rows → records_created=2, warnings=[]
7. `test_import_actuals_skips_invalid_rows` — 1 valid + 1 invalid → created=1, warnings=1
8. `test_import_actuals_unmapped_columns` — extra CSV column not in ALL_COLUMNS → appears in unmapped_columns

## Run Commands
```bash
cd backend && pytest tests/unit/actuals/ -v
cd backend && alembic upgrade head
cd backend && alembic downgrade -1 && alembic upgrade head
```

## Expected
```
8 passed
Migration up/down/up clean
```
