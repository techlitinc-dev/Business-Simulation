from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.blueprint_service import get_version_payload
from app.services.whatif.schemas import BreakevenRequest, BreakevenResult
from app.services.whatif.sweep import MONTHS, _patch_payload, _simulate_lifespans


async def find_breakeven(request: BreakevenRequest, db: AsyncSession) -> BreakevenResult:
    """
    Binary search for the parameter value where survival rate crosses target_survival.
    Uses 30 seeded simulations per candidate value for stability.
    """
    blueprint_payload = await get_version_payload(
        db,
        workspace_id=request.workspace_id,
        blueprint_id=request.blueprint_id,
        version=None,
    )
    payload_dict = blueprint_payload.model_dump(mode="json")
    mc_runs = 30

    def survival_at(value: float) -> float:
        patched = _patch_payload(payload_dict, request.param, value)
        lifespans = _simulate_lifespans(patched, mc_runs)
        return sum(1 for lifespan in lifespans if lifespan >= MONTHS) / mc_runs

    lo, hi = request.search_min, request.search_max
    target = request.target_survival
    max_iter = 20

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        s = survival_at(mid)
        if abs(s - target) < 0.02:  # within 2% = good enough
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
