"""Counter-factual optimization analysis (T31).

``estimate_survival_delta`` clones the Format A blueprint, applies exactly ONE
tweak, and re-runs the pure engine in-process with seeded RNGs — fully
deterministic, no Celery, no LLM.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from app.engine.loop import run_simulation
from app.engine.state import compile_blueprint
from app.schemas.report import TweakResult

#: Fixed candidate tweak set (spec §10 / T31).
TWEAK_KEYS = [
    "churn",
    "cac",
    "price",
    "fixed_monthly",
    "starting_capital",
    "client_concentration",
]


@dataclass(frozen=True)
class BlueprintTweak:
    key: str
    label: str


TWEAKS: list[BlueprintTweak] = [
    BlueprintTweak("churn", "Reduce churn by 20%"),
    BlueprintTweak("cac", "Reduce CAC by 20%"),
    BlueprintTweak("price", "Raise price by 10%"),
    BlueprintTweak("fixed_monthly", "Cut fixed costs by 15%"),
    BlueprintTweak("starting_capital", "Raise starting capital by 25%"),
    BlueprintTweak("client_concentration", "Cap client concentration at 25% of revenue"),
]


def apply_tweak(base_payload: dict[str, Any], tweak: BlueprintTweak) -> dict[str, Any]:
    """Clone the payload and apply exactly ONE variable change (pure)."""
    payload = copy.deepcopy(base_payload)
    streams = payload["revenue_engine"]["streams"]
    costs = payload["cost_structure"]
    financials = payload["financials"]

    if tweak.key == "churn":
        for s in streams:
            s["churn_monthly"] = round(float(s["churn_monthly"]) * 0.8, 4)
    elif tweak.key == "cac":
        for s in streams:
            s["cac"] = round(float(s["cac"]) * 0.8, 2)
    elif tweak.key == "price":
        for s in streams:
            s["price_point"] = round(float(s["price_point"]) * 1.1, 2)
    elif tweak.key == "fixed_monthly":
        costs["fixed_monthly"] = round(float(costs["fixed_monthly"]) * 0.85, 2)
        costs["burn_rate_month_1"] = round(
            float(costs["burn_rate_month_1"]) * 0.85, 2
        )
    elif tweak.key == "starting_capital":
        financials["starting_capital"] = round(
            float(financials["starting_capital"]) * 1.25, 2
        )
    elif tweak.key == "client_concentration":
        # Cap a single stream's share of projected month-12 revenue at 25%.
        # Model as equalizing projected customers across the streams.
        if len(streams) > 1:
            total = sum(
                float(s["projected_customers_month_12"]) for s in streams
            )
            share = 1.0 / len(streams)
            for s in streams:
                s["projected_customers_month_12"] = int(total * share)
        # A single stream is 100% concentrated by construction; the tweak
        # cannot redistribute without more streams — treat as a no-op there.
    else:  # pragma: no cover - guarded by the fixed tweak set
        raise ValueError(f"Unknown tweak: {tweak.key}")
    return payload


def _survival_rate(payload: dict[str, Any], n_runs: int, seed: int) -> float:
    survived = 0
    for i in range(n_runs):
        rng_seed = seed + i
        state = compile_blueprint(payload)
        result = run_simulation(state, 24, seed=rng_seed)
        if result.survived:
            survived += 1
    return survived / n_runs if n_runs else 0.0


def estimate_survival_delta(
    base_payload: dict[str, Any],
    tweak: BlueprintTweak,
    n_runs: int,
    seed: int,
) -> float:
    """Tweaked survival rate minus baseline, in percentage points.

    Deterministic: seeds are derived as ``seed + tweak_index * 1000 + run_index``.
    """
    tweak_index = TWEAK_KEYS.index(tweak.key)
    base_seed = seed + tweak_index * 1000
    baseline = _survival_rate(base_payload, n_runs, base_seed)
    tweaked_payload = apply_tweak(base_payload, tweak)
    tweaked = _survival_rate(tweaked_payload, n_runs, base_seed)
    return round((tweaked - baseline) * 100, 1)


def measure_all_tweaks(
    base_payload: dict[str, Any], *, n_runs: int = 20, seed: int = 42
) -> list[TweakResult]:
    """Measure every candidate tweak's survival delta (deterministic)."""
    baseline = _survival_rate(base_payload, n_runs, seed)
    results: list[TweakResult] = []
    for tweak in TWEAKS:
        tweak_index = TWEAK_KEYS.index(tweak.key)
        base_seed = seed + tweak_index * 1000
        tweaked = _survival_rate(apply_tweak(base_payload, tweak), n_runs, base_seed)
        results.append(
            TweakResult(
                tweak_key=tweak.key,
                label=tweak.label,
                delta_pp=round((tweaked - baseline) * 100, 1),
                baseline_survival=round(baseline, 4),
                tweaked_survival=round(tweaked, 4),
            )
        )
    return results
