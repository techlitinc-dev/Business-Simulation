from __future__ import annotations

import statistics
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.loop import run_simulation
from app.engine.state import compile_blueprint
from app.models.actuals import ActualsRecord
from app.models.blueprint import BlueprintVersion
from app.models.simulation import SimulationRun
from app.services.whatif.sweep import _patch_payload

MONTHS = 24


@dataclass
class VarianceDelta:
    blueprint_id: str
    month: int
    prior_survival_rate: float
    new_survival_rate: float
    survival_delta: float  # new - prior (negative = worse)
    prior_runway_median: float
    new_runway_median: float
    runway_delta: float
    prior_resilience_score: float
    new_resilience_score: float
    score_delta: float
    key_changes: list[str]  # human-readable change descriptions


def _survival_metrics(lifespans: list[float]) -> tuple[float, float]:
    """Survival rate + median runway from a set of seeded run lifespans."""
    survived = sum(1 for lifespan in lifespans if lifespan >= MONTHS)
    return survived / len(lifespans), statistics.median(lifespans)


def _resilience_score(survival_rate: float, median_runway: float) -> float:
    """0-100 heuristic matching the engine's survival-share + runway blend."""
    survival_component = survival_rate * 70.0
    runway_component = min(1.0, median_runway / MONTHS) * 30.0
    return max(0.0, min(100.0, survival_component + runway_component))


async def compute_variance(
    blueprint_id: str,
    workspace_id: uuid.UUID,
    db: AsyncSession,
    mc_runs: int = 50,
) -> VarianceDelta:
    """
    Re-baseline the blueprint from latest actuals and run new forecast.
    Compare survival rate, runway, and resilience score vs. the last simulation run.
    """
    # Get actuals ordered by month.
    result = await db.execute(
        select(ActualsRecord)
        .where(
            ActualsRecord.blueprint_id == blueprint_id,
            ActualsRecord.workspace_id == workspace_id,
        )
        .order_by(ActualsRecord.month)
    )
    actuals = result.scalars().all()
    if not actuals:
        raise ValueError("No actuals imported for this blueprint")

    # Get latest blueprint version (workspace-scoped lookup happens via the FK).
    bpv_result = await db.execute(
        select(BlueprintVersion)
        .where(BlueprintVersion.blueprint_id == blueprint_id)
        .order_by(BlueprintVersion.version.desc())
        .limit(1)
    )
    bpv = bpv_result.scalar_one_or_none()
    if bpv is None:
        raise ValueError("Blueprint version not found")

    original_payload = dict(bpv.payload)
    latest_actuals = actuals[-1]

    # Re-baseline: override blueprint fields with latest actuals month.
    patched_payload = original_payload.copy()
    for field, value in latest_actuals.fields.items():
        patched_payload = _patch_payload(patched_payload, field, value)

    # Run MC simulation with the patched payload (pure engine, seeded).
    state = compile_blueprint(patched_payload)
    new_lifespans = [
        float(run_simulation(state, MONTHS, seed=seed).months_simulated)
        for seed in range(mc_runs)
    ]
    new_survival, new_runway = _survival_metrics(new_lifespans)

    # Prior metrics from the most recent simulation run's stored result JSONB.
    prior_survival = 0.0
    prior_runway = 0.0
    prior_score = 0.0
    run_result = await db.execute(
        select(SimulationRun)
        .join(BlueprintVersion, SimulationRun.blueprint_version_id == BlueprintVersion.id)
        .where(BlueprintVersion.blueprint_id == blueprint_id)
        .order_by(SimulationRun.created_at.desc())
        .limit(1)
    )
    prior_run = run_result.scalar_one_or_none()
    if prior_run is not None and prior_run.result:
        prior_survival = float(prior_run.result.get("survival_rate", 0.0))
        prior_runway = float(prior_run.result.get("median_lifespan_months", 0.0))
        prior_score = float(prior_run.result.get("resilience_score", 0.0))

    # Key changes: actuals vs. the ORIGINAL blueprint payload (>5% relative move).
    key_changes: list[str] = []
    for field, value in latest_actuals.fields.items():
        original = _original_value(original_payload, field)
        if original is None:
            continue
        try:
            original_f = float(str(original))
            value_f = float(value)
        except (TypeError, ValueError):
            continue
        denom = abs(original_f) + 1e-9
        if abs(value_f - original_f) / denom > 0.05:
            direction = "increased" if value_f > original_f else "decreased"
            key_changes.append(f"{field} {direction} from {original_f:.2f} to {value_f:.2f}")

    new_score = _resilience_score(new_survival, new_runway)

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


def _original_value(payload: dict[str, object], field: str) -> object | None:
    """Read a dot-notation field from the original payload (None if absent)."""
    obj: object = payload
    for part in field.split("."):
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        elif isinstance(obj, list) and part.isdigit() and int(part) < len(obj):
            obj = obj[int(part)]
        else:
            return None
    return obj
