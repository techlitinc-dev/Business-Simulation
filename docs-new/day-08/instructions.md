# Day 08 — F-06: Parameter Sweep Engine + Break-Even Finder

## Feature
F-06: What-If Lab & Sensitivity Sweeps

## Goal
Implement a pure-engine (no LLM) parameter sweep that runs a grid of seeded simulations across a parameter range, and a binary-search break-even finder that identifies the exact parameter threshold where survival flips.

## Prerequisites
- Engine `tick` loop and `apply_event` functions exist in `app/engine/`
- `simulation_service.py` has baseline runner pattern to follow
- No new dependencies needed

---

## Step 1 — Create `backend/app/services/whatif/` package

```
backend/app/services/whatif/__init__.py
backend/app/services/whatif/schemas.py
backend/app/services/whatif/sweep.py
backend/app/services/whatif/breakeven.py
```

### `schemas.py`
```python
from pydantic import BaseModel, Field
from typing import Any


class SweepRequest(BaseModel):
    blueprint_id: str
    param: str = Field(..., description="e.g. 'monthly_churn', 'cac', 'price', 'fixed_monthly_costs'")
    min_value: float
    max_value: float
    steps: int = Field(default=10, ge=2, le=50)
    mc_runs: int = Field(default=20, ge=5, le=100, description="Simulations per grid point")


class SweepGridPoint(BaseModel):
    param_value: float
    survival_rate: float
    median_runway: float
    p25_runway: float
    p75_runway: float


class SweepResult(BaseModel):
    blueprint_id: str
    param: str
    grid: list[SweepGridPoint]
    breakeven_value: float | None = None


class BreakevenRequest(BaseModel):
    blueprint_id: str
    param: str
    search_min: float
    search_max: float
    target_survival: float = Field(default=0.5, ge=0.0, le=1.0)


class BreakevenResult(BaseModel):
    blueprint_id: str
    param: str
    breakeven_value: float
    survival_at_breakeven: float
    message: str
```

---

### `sweep.py`
```python
from __future__ import annotations
import statistics
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.whatif.schemas import SweepRequest, SweepResult, SweepGridPoint
from app.services.blueprint_service import get_blueprint_payload
from app.engine.runner import run_simulation  # existing engine entry point


async def run_sweep(request: SweepRequest, db: AsyncSession) -> SweepResult:
    """
    Run a grid of seeded engine simulations across param range.
    Pure engine — no LLM, no API calls.
    Each simulation runs in <100ms.
    """
    blueprint_payload = await get_blueprint_payload(request.blueprint_id, db)
    grid: list[SweepGridPoint] = []

    step_size = (request.max_value - request.min_value) / (request.steps - 1)
    param_values = [request.min_value + i * step_size for i in range(request.steps)]

    for param_value in param_values:
        # Patch the blueprint payload with the parameter override
        patched = _patch_payload(blueprint_payload, request.param, param_value)
        lifespans: list[float] = []

        for seed in range(request.mc_runs):
            result = run_simulation(patched, seed=seed, months=24)
            lifespans.append(result.get("final_month", 24))

        survived = [l for l in lifespans if l >= 24]
        survival_rate = len(survived) / len(lifespans)
        median_runway = statistics.median(lifespans)
        sorted_l = sorted(lifespans)
        n = len(sorted_l)
        p25 = sorted_l[max(0, int(n * 0.25))]
        p75 = sorted_l[min(n - 1, int(n * 0.75))]

        grid.append(SweepGridPoint(
            param_value=round(param_value, 6),
            survival_rate=round(survival_rate, 4),
            median_runway=round(median_runway, 2),
            p25_runway=round(p25, 2),
            p75_runway=round(p75, 2),
        ))

    return SweepResult(
        blueprint_id=request.blueprint_id,
        param=request.param,
        grid=grid,
    )


def _patch_payload(payload: dict, param: str, value: float) -> dict:
    """
    Override a single parameter in the blueprint payload dict.
    Supports dot-notation: e.g. 'financials.monthly_churn'
    """
    import copy
    patched = copy.deepcopy(payload)
    parts = param.split(".")
    obj = patched
    for part in parts[:-1]:
        obj = obj.setdefault(part, {})
    obj[parts[-1]] = value
    return patched
```

---

### `breakeven.py`
```python
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.whatif.schemas import BreakevenRequest, BreakevenResult
from app.services.blueprint_service import get_blueprint_payload
from app.services.whatif.sweep import _patch_payload
from app.engine.runner import run_simulation


async def find_breakeven(request: BreakevenRequest, db: AsyncSession) -> BreakevenResult:
    """
    Binary search for the parameter value where survival rate crosses target_survival.
    Uses 30 seeded simulations per candidate value for stability.
    """
    blueprint_payload = await get_blueprint_payload(request.blueprint_id, db)
    MC_RUNS = 30

    def survival_at(value: float) -> float:
        patched = _patch_payload(blueprint_payload, request.param, value)
        lifespans = [
            run_simulation(patched, seed=s, months=24).get("final_month", 24)
            for s in range(MC_RUNS)
        ]
        return sum(1 for l in lifespans if l >= 24) / MC_RUNS

    lo, hi = request.search_min, request.search_max
    target = request.target_survival
    MAX_ITER = 20

    for _ in range(MAX_ITER):
        mid = (lo + hi) / 2
        s = survival_at(mid)
        if abs(s - target) < 0.02:   # within 2% = good enough
            break
        # Assume higher param value → lower survival (e.g. higher churn = worse)
        if s > target:
            lo = mid
        else:
            hi = mid

    breakeven = (lo + hi) / 2
    final_survival = survival_at(breakeven)

    return BreakevenResult(
        blueprint_id=request.blueprint_id,
        param=request.param,
        breakeven_value=round(breakeven, 6),
        survival_at_breakeven=round(final_survival, 4),
        message=(
            f"Your model maintains ≥{target:.0%} survival "
            f"only if {request.param} stays below {breakeven:.4f}"
        ),
    )
```

---

## Step 2 — Test files

`backend/tests/unit/whatif/test_sweep.py`:
```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.whatif.schemas import SweepRequest
from app.services.whatif.sweep import run_sweep, _patch_payload


def test_patch_payload_flat():
    payload = {"monthly_churn": 0.05, "price": 99}
    result = _patch_payload(payload, "monthly_churn", 0.10)
    assert result["monthly_churn"] == 0.10
    assert payload["monthly_churn"] == 0.05  # original unchanged


def test_patch_payload_nested():
    payload = {"financials": {"monthly_churn": 0.05}}
    result = _patch_payload(payload, "financials.monthly_churn", 0.12)
    assert result["financials"]["monthly_churn"] == 0.12


def test_sweep_grid_has_correct_length():
    # Mock engine and blueprint service
    with patch("app.services.whatif.sweep.get_blueprint_payload", new_callable=AsyncMock) as mock_bp, \
         patch("app.services.whatif.sweep.run_simulation") as mock_run:
        mock_bp.return_value = {"monthly_churn": 0.05}
        mock_run.return_value = {"final_month": 18}

        req = SweepRequest(blueprint_id="bp_001", param="monthly_churn",
                           min_value=0.02, max_value=0.12, steps=6, mc_runs=5)
        result = asyncio.get_event_loop().run_until_complete(run_sweep(req, AsyncMock()))
        assert len(result.grid) == 6


def test_sweep_survival_rates_monotonic():
    """Higher churn → lower survival rate (monotonic relationship)."""
    with patch("app.services.whatif.sweep.get_blueprint_payload", new_callable=AsyncMock) as mock_bp, \
         patch("app.services.whatif.sweep.run_simulation") as mock_run:
        mock_bp.return_value = {"monthly_churn": 0.05}
        # Simulate: higher index (higher churn) → earlier death
        call_count = [0]
        def side_effect(payload, seed, months):
            call_count[0] += 1
            # crude: higher churn in payload → earlier death
            churn = payload.get("monthly_churn", 0.05)
            final_month = max(6, int(24 * (1 - churn * 5)))
            return {"final_month": final_month}
        mock_run.side_effect = side_effect

        req = SweepRequest(blueprint_id="bp_001", param="monthly_churn",
                           min_value=0.02, max_value=0.10, steps=5, mc_runs=5)
        result = asyncio.get_event_loop().run_until_complete(run_sweep(req, AsyncMock()))
        rates = [pt.survival_rate for pt in result.grid]
        # Should generally decrease (allow one non-monotonic due to randomness)
        decreases = sum(1 for a, b in zip(rates, rates[1:]) if a >= b)
        assert decreases >= 3


def test_sweep_result_serializable():
    import json
    with patch("app.services.whatif.sweep.get_blueprint_payload", new_callable=AsyncMock) as mock_bp, \
         patch("app.services.whatif.sweep.run_simulation") as mock_run:
        mock_bp.return_value = {}
        mock_run.return_value = {"final_month": 20}
        req = SweepRequest(blueprint_id="bp_001", param="price",
                           min_value=50, max_value=200, steps=3, mc_runs=3)
        result = asyncio.get_event_loop().run_until_complete(run_sweep(req, AsyncMock()))
        json.dumps(result.model_dump())  # must not raise
```

`backend/tests/unit/whatif/test_breakeven.py`:
```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.whatif.schemas import BreakevenRequest
from app.services.whatif.breakeven import find_breakeven


def test_breakeven_returns_result():
    with patch("app.services.whatif.breakeven.get_blueprint_payload", new_callable=AsyncMock) as mock_bp, \
         patch("app.services.whatif.breakeven.run_simulation") as mock_run:
        mock_bp.return_value = {"monthly_churn": 0.05}
        def side_effect(payload, seed, months):
            churn = payload.get("monthly_churn", 0.05)
            return {"final_month": 24 if churn < 0.07 else 14}
        mock_run.side_effect = side_effect

        req = BreakevenRequest(blueprint_id="bp_001", param="monthly_churn",
                               search_min=0.02, search_max=0.12, target_survival=0.5)
        result = asyncio.get_event_loop().run_until_complete(find_breakeven(req, AsyncMock()))
        assert 0.02 <= result.breakeven_value <= 0.12
        assert "monthly_churn" in result.message
        assert 0.0 <= result.survival_at_breakeven <= 1.0
```

---

## Verification Commands
```bash
cd backend && pytest tests/unit/whatif/ -v
cd backend && ruff check app/services/whatif/
cd backend && mypy app/services/whatif/ --ignore-missing-imports
```
