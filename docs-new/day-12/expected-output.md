# Day 12 — Expected Output

## Files Created
```
backend/app/models/actuals.py
backend/app/services/actuals/__init__.py
backend/app/services/actuals/schemas.py
backend/app/services/actuals/importer.py
backend/alembic/versions/xxxx_actuals_table.py
backend/tests/unit/actuals/__init__.py
backend/tests/unit/actuals/test_importer.py
```

## Alembic Migration
```
$ alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade f7a8b9c0d1e2 -> g8h9i0j1k2l3, add actuals_records table
```

## DB Table Created
```sql
CREATE TABLE actuals_records (
  id VARCHAR PRIMARY KEY,
  blueprint_id VARCHAR NOT NULL,
  workspace_id VARCHAR NOT NULL,
  month INTEGER NOT NULL,
  period_label VARCHAR,
  fields JSON NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ
);
```

## Sample Import Result
```json
{
  "records_created": 3,
  "records_updated": 0,
  "validation_warnings": [],
  "unmapped_columns": []
}
```

## Validation Warning Example
```json
{
  "records_created": 2,
  "records_updated": 0,
  "validation_warnings": [{"row": 4, "errors": ["Field 'revenue' must be numeric, got: 'invalid'"]}],
  "unmapped_columns": ["notes"]
}
```

## Pytest: 8 passed
