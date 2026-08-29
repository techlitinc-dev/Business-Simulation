# Day 13 — F-04: Plan-vs-Simulation Variance Engine + DeepSeek Narrative

## Feature
F-04: Living Blueprint & Plan-vs-Actuals

## Goal
Implement `variance.py` that re-baselines the blueprint from uploaded actuals and re-runs the forecast. Implement `variance_narrator.py` that calls DeepSeek to produce a plain-English explanation of the variance delta.

## Prerequisites
- Day 12 complete (ActualsRecord model, importer)
- Existing `simulation_service.py` baseline runner
- Existing `bridge.py` for DeepSeek calls

---

## Step 1 — Create `backend/app/services/actuals/variance.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actuals import ActualsRecord
from app.models.simulation import SimulationRun
from app.models.blueprint import BlueprintVersion
from app.services.whatif.sweep import _patch_payload
from app.engine.runner import run_simulation


@dataclass
class VarianceDelta:
    blueprint_id: str
    month: int
    prior_survival_rate: float
    new_survival_rate: float
    survival_delta: float          # new - prior (negative = worse)
    prior_runway_median: float
    new_runway_median: float
    runway_delta: float
    prior_resilience_score: float
    new_resilience_score: float
    score_delta: float
    key_changes: list[str]         # human-readable change descriptions


async def compute_variance(
    blueprint_id: str,
    workspace_id: str,
    db: AsyncSession,
    mc_runs: int = 50,
) -> VarianceDelta:
    """
    Re-baseline the blueprint from latest actuals and run new forecast.
    Compare survival rate, runway, and resilience score vs. the last simulation run.
    """
    # Get actuals ordered by month
    result = await db.execute(
        select(ActualsRecord)
        .where(ActualsRecord.blueprint_id == blueprint_id,
               ActualsRecord.workspace_id == workspace_id)
        .order_by(ActualsRecord.month)
    )
    actuals = result.scalars().all()
    if not actuals:
        raise ValueError("No actuals imported for this blueprint")

    # Get latest blueprint version
    bpv_result = await db.execute(
        select(BlueprintVersion)
        .where(BlueprintVersion.blueprint_id == blueprint_id)
        .order_by(BlueprintVersion.created_at.desc()).limit(1)
    )
    bpv = bpv_result.scalar_one_or_none()
    if bpv is None:
        raise ValueError("Blueprint version not found")

    # Re-baseline: override blueprint fields with latest actuals month
    latest_actuals = actuals[-1]
    patched_payload = bpv.payload.copy()
    for field, value in latest_actuals.fields.items():
        patched_payload = _patch_payload(patched_payload, field, value)

    # Run MC simulation with patched payload
    new_lifespans = [
        run_simulation(patched_payload, seed=s, months=24).get("final_month", 24)
        for s in range(mc_runs)
    ]
    new_survival = sum(1 for l in new_lifespans if l >= 24) / mc_runs
    import statistics
    new_runway = statistics.median(new_lifespans)

    # Get prior survival from last SimulationRun mc_result
    run_result = await db.execute(
        select(SimulationRun)
        .where(SimulationRun.blueprint_id == blueprint_id)
        .order_by(SimulationRun.created_at.desc()).limit(1)
    )
    prior_run = run_result.scalar_one_or_none()
    prior_survival = 0.0
    prior_runway = 0.0
    if prior_run and prior_run.mc_result:
        prior_survival = prior_run.mc_result.get("survival_rate", 0.0)
        prior_runway = prior_run.mc_result.get("median_lifespan", 0.0)

    # Compute key changes
    key_changes = []
    for field, value in latest_actuals.fields.items():
        original = patched_payload.get(field)
        if original is not None and abs(float(value) - float(original)) / (abs(float(original)) + 1e-9) > 0.05:
            direction = "increased" if float(value) > float(original) else "decreased"
            key_changes.append(f"{field} {direction} from {original:.2f} to {value:.2f}")

    from app.engine.metrics import resilience_score
    new_score = resilience_score({"survival_rate": new_survival, "median_lifespan": new_runway})
    prior_score = resilience_score({"survival_rate": prior_survival, "median_lifespan": prior_runway})

    return VarianceDelta(
        blueprint_id=blueprint_id,
        month=latest_actuals.month,
        prior_survival_rate=round(prior_survival, 4),
        new_survival_rate=round(new_survival, 4),
        survival_delta=round(new_survival - prior_survival, 4),
        prior_runway_median=round(prior_runway, 2),
        new_runway_median=round(new_runway, 2),
        runway_delta=round(new_runway - prior_runway, 2),
        prior_resilience_score=round(prior_score, 2),
        new_resilience_score=round(new_score, 2),
        score_delta=round(new_score - prior_score, 2),
        key_changes=key_changes,
    )
```

---

## Step 2 — Create `backend/app/agents/variance_narrator.py`

```python
from __future__ import annotations
import json
import logging
from app.agents.bridge import generate_structured
from app.agents.llm.factory import get_provider
from app.services.actuals.variance import VarianceDelta
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VarianceNarrativeOutput(BaseModel):
    headline: str = Field(..., description="One-sentence summary of the change")
    explanation: str = Field(..., min_length=100, description="2-3 paragraph explanation")
    primary_driver: str = Field(..., description="The single most impactful factor")
    outlook: str = Field(..., description="1-sentence forward-looking statement")


async def narrate_variance(delta: VarianceDelta) -> VarianceNarrativeOutput:
    """
    Call DeepSeek to generate a plain-English explanation of the variance delta.
    All numbers in the output are grounded in the delta object — no fabrication.
    """
    provider = get_provider()
    prompt = f"""You are a business analyst explaining simulation variance to a founder.

VARIANCE DATA:
{json.dumps({
    "month": delta.month,
    "survival_rate_change": f"{delta.prior_survival_rate:.0%} → {delta.new_survival_rate:.0%} ({delta.survival_delta:+.0%})",
    "runway_change": f"{delta.prior_runway_median:.1f} → {delta.new_runway_median:.1f} months ({delta.runway_delta:+.1f})",
    "resilience_score_change": f"{delta.prior_resilience_score:.1f} → {delta.new_resilience_score:.1f} ({delta.score_delta:+.1f})",
    "key_changes": delta.key_changes,
}, indent=2)}

RULES:
- headline: one sentence using exact numbers from the data above.
- explanation: 2-3 paragraphs explaining the variance. Reference the key_changes.
- primary_driver: the single most impactful change from key_changes.
- outlook: 1 forward-looking sentence.
- Do NOT invent numbers. Use only the values provided above.
"""
    result = await generate_structured(
        provider=provider,
        system_prompt=prompt,
        user_message="Explain this variance to the founder.",
        response_schema=VarianceNarrativeOutput,
    )
    logger.info(f"[variance_narrator] Generated narrative for blueprint {delta.blueprint_id} month {delta.month}")
    return result
```

---

## Step 3 — Create prompt file

`backend/app/agents/prompts/variance_narrative.md`:
```markdown
You are a business analyst explaining simulation variance to a founder.
Generate structured JSON output matching the VarianceNarrativeOutput schema.
All numbers must come from the provided variance data. Never fabricate metrics.
```

---

## Step 4 — Tests

`backend/tests/unit/actuals/test_variance.py`:
```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.actuals.variance import compute_variance


def test_compute_variance_with_actuals():
    mock_db = AsyncMock()

    # Mock actuals
    actual = MagicMock()
    actual.month = 3
    actual.fields = {"monthly_churn": 0.08, "revenue": 15000}

    # Mock blueprint version
    bpv = MagicMock()
    bpv.payload = {"monthly_churn": 0.05, "revenue": 12000, "starting_capital": 100000}

    # Mock prior run
    prior_run = MagicMock()
    prior_run.mc_result = {"survival_rate": 0.72, "median_lifespan": 19.0}
    prior_run.blueprint_id = "bp_001"

    mock_db.execute = AsyncMock(side_effect=[
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[actual])))),
        MagicMock(scalar_one_or_none=MagicMock(return_value=bpv)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=prior_run)),
    ])

    with patch("app.services.actuals.variance.run_simulation") as mock_run:
        mock_run.return_value = {"final_month": 16}  # worse than before
        result = asyncio.get_event_loop().run_until_complete(
            compute_variance("bp_001", "ws_001", mock_db, mc_runs=5)
        )

    assert result.blueprint_id == "bp_001"
    assert result.survival_delta <= 0   # worse (all runs finish at 16 < 24)
    assert isinstance(result.key_changes, list)


def test_compute_variance_no_actuals_raises():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    ))
    with pytest.raises(ValueError, match="No actuals"):
        asyncio.get_event_loop().run_until_complete(
            compute_variance("bp_001", "ws_001", mock_db)
        )
```

---

## Verification Commands
```bash
cd backend && pytest tests/unit/actuals/ -v
cd backend && ruff check app/services/actuals/variance.py app/agents/variance_narrator.py
```
