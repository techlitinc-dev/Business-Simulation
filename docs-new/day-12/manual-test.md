# Day 12 — Manual Test Checklist

## Checklist

### 1. Run alembic migration
```bash
cd backend && alembic upgrade head
```
- [ ] Migration runs without error
- [ ] `actuals_records` table exists in DB: `\dt actuals_records` in psql

### 2. Import actuals via Python shell
```python
import asyncio
from app.db.session import AsyncSessionLocal
from app.services.actuals.importer import import_actuals
from app.services.actuals.schemas import ActualsUploadRequest

csv = """month,revenue,costs,cash,churn_rate
1,12000,14000,86000,0.05
2,15000,14200,86800,0.04
3,18000,14500,90300,0.03
"""
req = ActualsUploadRequest(blueprint_id="<bp_id>", csv_content=csv)
async def run():
    async with AsyncSessionLocal() as db:
        return await import_actuals(req, "<workspace_id>", db)
result = asyncio.run(run())
print(result)
```
- [ ] records_created=3
- [ ] validation_warnings=[]
- [ ] unmapped_columns=[]

### 3. Verify records in DB
```sql
SELECT * FROM actuals_records WHERE blueprint_id = '<bp_id>';
```
- [ ] 3 rows returned
- [ ] fields JSON contains correct revenue, costs, cash values

### 4. Test duplicate import (update path)
- [ ] Import same CSV again
- [ ] records_created=0, records_updated=3

### 5. Test invalid row
```python
csv_bad = "month,revenue\n1,12000\nbad,notanumber"
req2 = ActualsUploadRequest(blueprint_id="<bp_id>", csv_content=csv_bad)
result2 = asyncio.run(run_with(req2))
print(result2.validation_warnings)
```
- [ ] 1 warning for row 3
- [ ] Only 1 record created

### 6. Migration rollback/re-apply
```bash
cd backend && alembic downgrade -1 && alembic upgrade head
```
- [ ] Both commands succeed cleanly
