from __future__ import annotations

import copy
import statistics
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.loop import run_simulation
from app.engine.state import compile_blueprint
from app.services.blueprint_service import get_version_payload
from app.services.whatif.schemas import SweepGridPoint, SweepRequest, SweepResult

MONTHS = 24


def _patch_payload(payload: dict[str, Any], param: str, value: float) -> dict[str, Any]:
    """
    Override a single parameter in the blueprint payload dict.
    Supports dot-notation: e.g. 'financials.starting_capital' or
    'revenue_engine.streams.0.churn_monthly'.
    """
    patched = copy.deepcopy(payload)
    parts = param.split(".")
    obj: Any = patched
    for part in parts[:-1]:
        obj = obj[int(part)] if isinstance(obj, list) else obj.setdefault(part, {})
    if isinstance(obj, list):
        obj[int(parts[-1])] = value
    else:
        obj[parts[-1]] = value
    return patched


def _simulate_lifespans(
    payload: dict[str, Any], n_runs: int, base_seed: int = 0
) -> list[float]:
    """Run ``n_runs`` seeded simulations; return months survived per run."""
    state = compile_blueprint(payload)
    lifespans: list[float] = []
    for seed in range(base_seed, base_seed + n_runs):
        result = run_simulation(state, MONTHS, seed=seed)
        lifespans.append(float(result.months_simulated))
    return lifespans


async def run_sweep(request: SweepRequest, db: AsyncSession) -> SweepResult:
    """
    Run a grid of seeded engine simulations across param range.
    Pure engine — no LLM, no API calls.
    Each simulation runs in <100ms.
    """
    blueprint_payload = await get_version_payload(
        db,
        workspace_id=request.workspace_id,
        blueprint_id=request.blueprint_id,
        version=None,
    )
    payload_dict = blueprint_payload.model_dump(mode="json")
    grid: list[SweepGridPoint] = []

    step_size = (request.max_value - request.min_value) / (request.steps - 1)
    param_values = [request.min_value + i * step_size for i in range(request.steps)]

    for param_value in param_values:
        patched = _patch_payload(payload_dict, request.param, param_value)
        lifespans = _simulate_lifespans(patched, request.mc_runs)

        survived = [lifespan for lifespan in lifespans if lifespan >= MONTHS]
        survival_rate = len(survived) / len(lifespans)
        median_runway = statistics.median(lifespans)
        sorted_l = sorted(lifespans)
        n = len(sorted_l)
        p25 = sorted_l[max(0, int(n * 0.25))]
        p75 = sorted_l[min(n - 1, int(n * 0.75))]

        grid.append(
            SweepGridPoint(
                param_value=round(param_value, 6),
                survival_rate=round(survival_rate, 4),
                median_runway=round(median_runway, 2),
                p25_runway=round(p25, 2),
                p75_runway=round(p75, 2),
            )
        )

    return SweepResult(
        blueprint_id=request.blueprint_id,
        param=request.param,
        grid=grid,
    )
