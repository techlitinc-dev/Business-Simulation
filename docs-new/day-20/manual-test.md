# Day 20 — Manual Test Checklist

## Checklist

### 1. Run migration
```bash
cd backend && alembic upgrade head
```
- [ ] `benchmark_snapshots` table created

### 2. Seed some benchmark data and query
```python
import asyncio
from app.db.session import AsyncSessionLocal
from app.services.benchmark.aggregator import snapshot_run, get_cohort_stats, score_percentile

async def seed_and_query():
    async with AsyncSessionLocal() as db:
        for i in range(10):
            await snapshot_run(f"run_{i}", survival_rate=0.5 + i*0.04,
                median_lifespan=14 + i, resilience_score=50 + i*3,
                kill_vectors=[{"type":"cash_out","frequency":0.4}],
                industry="saas", stage="seed", db=db)
        stats = await get_cohort_stats("saas", "seed", db)
        print(stats)
        pct = await score_percentile(68.0, "saas", "seed", db)
        print(pct.label)

asyncio.run(seed_and_query())
```
- [ ] CohortStats returned with sample_size=10
- [ ] Percentile label: "Xth percentile vs. saas seed simulations"

### 3. Test < 5 samples returns None
```python
async with AsyncSessionLocal() as db:
    stats = await get_cohort_stats("restaurant", "series-a", db)
    print(stats)  # None — no data for this cohort
```
- [ ] Returns None

### 4. Verify opt-in toggle
- [ ] Add a snapshot with `opted_in=False`
- [ ] Verify it does NOT appear in cohort stats

### 5. Run pytest
```bash
cd backend && pytest tests/unit/benchmark/ -v
```
- [ ] 7 passed
