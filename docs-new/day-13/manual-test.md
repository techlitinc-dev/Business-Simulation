# Day 13 — Manual Test Checklist

## Checklist

### 1. Import actuals and compute variance
```python
import asyncio
from app.db.session import AsyncSessionLocal
from app.services.actuals.variance import compute_variance

async def run():
    async with AsyncSessionLocal() as db:
        return await compute_variance("<bp_id>", "<ws_id>", db, mc_runs=20)

delta = asyncio.run(run())
print(f"Survival: {delta.prior_survival_rate:.0%} → {delta.new_survival_rate:.0%}")
print(f"Key changes: {delta.key_changes}")
```
- [ ] Returns VarianceDelta without error
- [ ] survival_delta is negative when actuals show worse churn than blueprint assumed
- [ ] key_changes lists the fields that changed

### 2. Generate variance narrative
```python
from app.agents.variance_narrator import narrate_variance
narrative = asyncio.run(narrate_variance(delta))
print(narrative.headline)
print(narrative.explanation[:200])
```
- [ ] headline contains survival rate percentages
- [ ] explanation references primary_driver
- [ ] No hallucinated numbers (check vs. actual delta values)

### 3. Verify numbers are grounded
- [ ] Pick a number from the narrative (e.g. "14pp")
- [ ] Verify it matches delta.survival_delta * 100

### 4. Full pytest
```bash
cd backend && pytest tests/unit/actuals/ -v
```
- [ ] 13 passing
