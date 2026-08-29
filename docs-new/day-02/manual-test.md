# Day 02 — Manual Test Checklist

## Prerequisites
- A completed simulation run exists in the DB (run a baseline + MC run first)
- Backend running with DB access

## Checklist

### 1. Build data pack in a Python shell for a real run
```python
import asyncio
from app.db.session import AsyncSessionLocal
from app.services.deep_report.data_pack import build_data_pack
from app.services.deep_report.manifest import SectionDef, DataInputKey

section = SectionDef(section_number=2, title="Executive Summary", page_budget=2,
    data_inputs=[DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES, DataInputKey.FORGE_VULNERABILITIES],
    prompt_template="executive_summary.md")

async def run():
    async with AsyncSessionLocal() as db:
        return await build_data_pack(section, "<your_run_id>", db)

pack = asyncio.run(run())
print(pack.keys())         # dict_keys(['tick_logs', 'mc_aggregates', 'forge_vulnerabilities'])
print(len(pack["tick_logs"]))  # should equal number of simulated months (e.g. 24)
```
- [ ] No exception
- [ ] `tick_logs` list has 24 entries
- [ ] `mc_aggregates` dict has `survival_rate` key
- [ ] `forge_vulnerabilities` is a list (may be empty if review not run)

### 2. Verify determinism
- [ ] Call `build_data_pack` twice with same run_id
- [ ] Both results are identical: `pack1 == pack2` → `True`

### 3. Validate serialization
```python
import json
print(json.dumps(pack, default=str)[:200])
```
- [ ] No `TypeError`, JSON string is printed

### 4. Run validate_data_pack
```python
from app.services.deep_report.data_pack import validate_data_pack
warnings = validate_data_pack(pack, section)
print(warnings)  # [] if all keys populated
```
- [ ] Returns empty list when all keys populated
- [ ] Returns warning when a key is None

### 5. Run full pytest — no regressions
```bash
cd backend && pytest --tb=short -q
```
- [ ] All previous tests pass
- [ ] 10 new tests pass
