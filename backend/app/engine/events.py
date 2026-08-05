"""Deterministic bridge between AI-generated hurdles and engine physics (T15)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, replace

from app.engine.market import apply_competitor_shock
from app.engine.state import BusinessState, RevenueStream

_ALLOWED_IMMEDIATE_KEYS = {
    "cac_delta_percent",
    "churn_delta_percent",
    "new_signups_delta_percent",
    "team_morale_delta",
    "cash_burn_delta_monthly",
    "cash_delta_one_time",
    "price_delta_percent",
    "mrr_delta_percent",
    "competitor_pressure_delta",
    "sentiment_delta",
}

# Anti-LLM-hallucination clamps (plan.md Risks: the engine clamps deltas to
# physical possibility).
_PERCENT_MIN, _PERCENT_MAX = -90.0, 200.0
_MORALE_MIN, _MORALE_MAX = -1.0, 1.0
_PRESSURE_MIN, _PRESSURE_MAX = -0.8, 0.8
_SENTIMENT_MIN, _SENTIMENT_MAX = -1.0, 1.0

_CHURN_FLOOR, _CHURN_CEIL = 0.001, 0.95


@dataclass
class ActiveEffect:
    """A persistent event effect decaying linearly to zero."""

    remaining_months: int
    deltas: dict[str, float]


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def validate_mechanical_impact(raw: dict[str, object]) -> dict[str, float]:
    """Validate an immediate-impact dict; drop unknown keys, default missing to 0, clamp."""
    if not isinstance(raw, dict):
        raw = {}
    immediate = raw.get("immediate", raw) if isinstance(raw, dict) else {}
    if not isinstance(immediate, dict):
        immediate = {}

    cleaned: dict[str, float] = {}
    for key in _ALLOWED_IMMEDIATE_KEYS:
        value = immediate.get(key, 0.0)
        if not isinstance(value, (int, float)):
            value = 0.0
        value = float(value)
        if key.endswith("_delta_percent") or key == "cac_delta_percent":
            value = _clamp(value, _PERCENT_MIN, _PERCENT_MAX)
        elif key == "team_morale_delta":
            value = _clamp(value, _MORALE_MIN, _MORALE_MAX)
        elif key == "competitor_pressure_delta":
            value = _clamp(value, _PRESSURE_MIN, _PRESSURE_MAX)
        elif key == "sentiment_delta":
            value = _clamp(value, _SENTIMENT_MIN, _SENTIMENT_MAX)
        cleaned[key] = value

    for key in set(immediate) - _ALLOWED_IMMEDIATE_KEYS:
        warnings.warn(f"dropping unknown mechanical impact key: {key}", stacklevel=2)

    return cleaned


def _apply_percent_to_streams(
    streams: list[RevenueStream], key: str, delta: float
) -> list[RevenueStream]:
    """Multiplicatively adjust each stream by delta percent for churn / CAC / price."""
    updated = []
    for stream in streams:
        if key == "churn_monthly":
            new_churn = stream.churn_monthly * (1.0 + delta / 100.0)
            new_churn = _clamp(new_churn, _CHURN_FLOOR, _CHURN_CEIL)
            updated.append(replace(stream, churn_monthly=new_churn))
        elif key == "cac":
            new_cac = stream.cac * (1.0 + delta / 100.0)
            updated.append(replace(stream, cac=max(1.0, new_cac)))
        elif key == "price":
            new_price = stream.price_point * (1.0 + delta / 100.0)
            updated.append(replace(stream, price_point=max(0.01, new_price)))
        else:  # pragma: no cover - only churn/cac/price keys reach here
            updated.append(stream)
    return updated


def apply_event(
    state: BusinessState,
    mechanical_impact: dict[str, object],
    month: int,
    duration_months: int = 3,
) -> BusinessState:
    """Apply validated mechanical deltas to a NEW BusinessState; never mutates input."""
    impact = validate_mechanical_impact(mechanical_impact)
    fin = state.financials
    market = state.market
    streams = list(state.streams)

    cash = fin.cash + impact.get("cash_delta_one_time", 0.0)
    fixed_monthly = fin.fixed_monthly + impact.get("cash_burn_delta_monthly", 0.0)

    if impact.get("churn_delta_percent", 0.0) != 0.0:
        streams = _apply_percent_to_streams(streams, "churn_monthly", impact["churn_delta_percent"])
    if impact.get("cac_delta_percent", 0.0) != 0.0:
        streams = _apply_percent_to_streams(streams, "cac", impact["cac_delta_percent"])
    if impact.get("price_delta_percent", 0.0) != 0.0:
        streams = _apply_percent_to_streams(streams, "price", impact["price_delta_percent"])
    if impact.get("mrr_delta_percent", 0.0) != 0.0:
        # Scale each stream's price by the MRR delta (revenue moves with price).
        streams = _apply_percent_to_streams(streams, "price", impact["mrr_delta_percent"])

    if impact.get("competitor_pressure_delta", 0.0) != 0.0 or impact.get(
        "sentiment_delta", 0.0
    ) != 0.0:
        market = apply_competitor_shock(
            market,
            impact.get("competitor_pressure_delta", 0.0),
            impact.get("sentiment_delta", 0.0),
        )

    fin = replace(
        fin,
        cash=cash,
        fixed_monthly=fixed_monthly,
        monthly_burn=fin.monthly_burn + impact.get("cash_burn_delta_monthly", 0.0),
    )

    new_state = BusinessState(
        month=state.month,
        financials=fin,
        market=market,
        streams=streams,
        triggers_fired=list(state.triggers_fired),
        active_event_effects=list(state.active_event_effects),
        bankrupt=state.bankrupt,
    )

    persistent: dict[str, float] = {}
    if impact.get("new_signups_delta_percent", 0.0) != 0.0:
        persistent["new_signups_delta_percent"] = impact["new_signups_delta_percent"]
    if impact.get("churn_delta_percent", 0.0) != 0.0:
        persistent["churn_delta_percent"] = impact["churn_delta_percent"]
    if persistent:
        new_state.active_event_effects.append(
            ActiveEffect(remaining_months=duration_months, deltas=persistent).__dict__
        )

    return new_state


def apply_due_events(state: BusinessState, month: int) -> BusinessState:
    """Decay each active effect by one month and drop expired ones."""
    surviving = []
    for raw in state.active_event_effects:
        effect = ActiveEffect(**raw)
        effect.remaining_months -= 1
        if effect.remaining_months > 0:
            surviving.append(effect.__dict__)
    return replace(state, active_event_effects=surviving)
