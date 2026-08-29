# Day 16 — Manual Test Checklist

## Checklist

### 1. Run advisory board in shell
```python
import asyncio, os
os.environ["LLM_PROVIDER"] = "mock"
from app.agents.advisory_board import run_advisory_board
result = asyncio.run(run_advisory_board(
    {"monthly_churn": 0.05, "price": 99, "cac": 450, "starting_capital": 100000},
    {"survival_rate": 0.58, "resilience_score": 54.0, "median_lifespan": 14}
))
print([r["persona"] for r in result["reviews"]])
print(result["summary"]["overall_risk_level"])
```
- [ ] 4 personas returned
- [ ] Personas: CFO, CMO, RiskAuditor, Operator
- [ ] overall_risk_level is one of LOW/MEDIUM/HIGH/CRITICAL

### 2. Check distinct persona voices
- [ ] CFO review mentions financial metrics
- [ ] CMO review mentions growth/acquisition
- [ ] RiskAuditor review mentions failure probability
- [ ] Operator review mentions team/execution

### 3. Verify parallel execution speed
- [ ] Board review with MockProvider completes in <2s (4 calls run in parallel)

### 4. Run pytest
```bash
cd backend && pytest tests/unit/agents/test_advisory_board.py -v
```
- [ ] 6 passed
