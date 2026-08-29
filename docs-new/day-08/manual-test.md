# Day 08 — Manual Test Checklist

## Checklist

### 1. Run a sweep in Python shell
```python
import asyncio
from app.services.whatif.schemas import SweepRequest
from app.services.whatif.sweep import run_sweep
from app.db.session import AsyncSessionLocal

req = SweepRequest(
    blueprint_id="<your_blueprint_id>",
    param="monthly_churn",
    min_value=0.02, max_value=0.12, steps=6, mc_runs=10
)
async def run():
    async with AsyncSessionLocal() as db:
        return await run_sweep(req, db)

result = asyncio.run(run())
print([(pt.param_value, pt.survival_rate) for pt in result.grid])
```
- [ ] No exception
- [ ] 6 grid points returned
- [ ] Survival rates generally decrease as churn increases
- [ ] Values are between 0.0 and 1.0

### 2. Run break-even finder
```python
from app.services.whatif.schemas import BreakevenRequest
from app.services.whatif.breakeven import find_breakeven

req = BreakevenRequest(
    blueprint_id="<your_blueprint_id>",
    param="monthly_churn",
    search_min=0.02, search_max=0.15
)
async def run():
    async with AsyncSessionLocal() as db:
        return await find_breakeven(req, db)

result = asyncio.run(run())
print(result.message)
```
- [ ] Returns message: "Your model maintains ≥50% survival only if monthly_churn stays below X.XXXX"
- [ ] breakeven_value is between 0.02 and 0.15

### 3. Verify _patch_payload doesn't mutate original
```python
from app.services.whatif.sweep import _patch_payload
original = {"monthly_churn": 0.05}
patched = _patch_payload(original, "monthly_churn", 0.10)
assert original["monthly_churn"] == 0.05   # unchanged
assert patched["monthly_churn"] == 0.10    # patched
print("Immutability: OK")
```
- [ ] "Immutability: OK" printed

### 4. Confirm no LLM calls during sweep
- [ ] Check that `LLM_PROVIDER=mock` vs `LLM_PROVIDER=deepseek` produces identical sweep results
- [ ] No DeepSeek API calls logged during sweep (grep backend logs)

### 5. Run full pytest suite
```bash
cd backend && pytest --tb=short -q
```
- [ ] All previous tests pass
- [ ] 8 new tests pass
