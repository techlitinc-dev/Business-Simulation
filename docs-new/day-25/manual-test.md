# Day 25 — Manual Test Checklist

## Checklist

### 1. Run migration
```bash
cd backend && alembic upgrade head
```
- [ ] portfolios and portfolio_memberships tables created

### 2. Create portfolio in shell
```python
import asyncio
from app.db.session import AsyncSessionLocal
from app.services.portfolio.portfolio_service import create_portfolio, add_workspace, get_portfolio_summary

async def run():
    async with AsyncSessionLocal() as db:
        pf = await create_portfolio("Test Portfolio", "<user_id>", db)
        await add_workspace(pf.id, "<workspace_id_1>", "Company A", db)
        await add_workspace(pf.id, "<workspace_id_2>", "Company B", db)
        summary = await get_portfolio_summary(pf.id, db)
        print(summary)

asyncio.run(run())
```
- [ ] Portfolio created with 2 members
- [ ] Summary returns sorted workspace list
- [ ] avg_resilience_score computed

### 3. Remove workspace
```python
await remove_workspace(pf.id, "<workspace_id_2>", db)
summary2 = await get_portfolio_summary(pf.id, db)
print(summary2.member_count)  # 1
```
- [ ] member_count is 1 after removal
- [ ] workspace 2 data still exists in its own tables

### 4. Run pytest
```bash
cd backend && pytest tests/unit/portfolio/ -v
```
- [ ] 5 passed
