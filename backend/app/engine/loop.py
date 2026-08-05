"""The deterministic monthly time-step loop and trigger checks (spec §5)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace

from app.engine.financials import apply_cash_flow, compute_costs, compute_revenue, runway_months
from app.engine.market import compute_demand, update_market
from app.engine.state import BusinessState, Trigger, TriggerEvent

_MILESTONE_100_CUSTOMERS = 100
_MILESTONE_1M_ARR = 1_000_000
_FUNDING_NEED_RUNWAY = 6.0


@dataclass
class TickLog:
    """KPI snapshot recorded once per simulated month (spec §5 step 8)."""

    month: int
    kpis: dict[str, float] = field(default_factory=dict)


@dataclass
class SimulationResult:
    """Outcome of a full simulation run."""

    final_state: BusinessState
    tick_logs: list[TickLog]
    triggers: list[TriggerEvent]
    survived: bool
    months_simulated: int


def _milestone_fired(state: BusinessState, detail: str) -> bool:
    return any(
        ev.trigger == Trigger.MILESTONE and ev.detail == detail for ev in state.triggers_fired
    )


def check_triggers(state: BusinessState) -> list[TriggerEvent]:
    """Spec §5 step 5: fire bankruptcy, profitability, funding-need, milestone triggers."""
    fired: list[TriggerEvent] = []
    fin = state.financials

    if state.bankrupt:
        return fired

    if fin.cash < 0:
        state.bankrupt = True
        fired.append(TriggerEvent(state.month, Trigger.BANKRUPTCY, "cash balance negative"))
        return fired

    # Net income = revenue - total_costs = -monthly_burn (burn is signed).
    if -fin.monthly_burn > 0:
        fin.profitable_streak += 1
        if (
            fin.profitable_streak >= 3
            and not any(ev.trigger == Trigger.PROFITABILITY for ev in state.triggers_fired)
        ):
            fired.append(
                TriggerEvent(state.month, Trigger.PROFITABILITY, "3 consecutive profitable months")
            )
    else:
        fin.profitable_streak = 0

    burn = fin.monthly_burn
    runway_is_low = burn > 0 and runway_months(fin.cash, burn) < _FUNDING_NEED_RUNWAY
    already_fired = any(ev.trigger == Trigger.FUNDING_NEED for ev in state.triggers_fired)
    if runway_is_low and not already_fired:
        detail = f"runway below {_FUNDING_NEED_RUNWAY:g} months"
        fired.append(TriggerEvent(state.month, Trigger.FUNDING_NEED, detail))

    total_customers = sum(s.customers for s in state.streams)
    if total_customers >= _MILESTONE_100_CUSTOMERS and not _milestone_fired(state, "100 customers"):
        fired.append(TriggerEvent(state.month, Trigger.MILESTONE, "100 customers"))
    if fin.arr >= _MILESTONE_1M_ARR and not _milestone_fired(state, "$1M ARR"):
        fired.append(TriggerEvent(state.month, Trigger.MILESTONE, "$1M ARR"))

    return fired


def _effective_deltas(state: BusinessState) -> dict[str, float]:
    """Aggregate persistent event-effect deltas still active this month."""
    signups = 0.0
    churn = 0.0
    for effect in state.active_event_effects:
        deltas = effect.get("deltas", {})
        if not isinstance(deltas, dict):
            continue
        signups += float(deltas.get("new_signups_delta_percent", 0.0))
        churn += float(deltas.get("churn_delta_percent", 0.0))
    return {"new_signups_delta_percent": signups, "churn_delta_percent": churn}


def _customer_movement(prev: BusinessState, state: BusinessState) -> tuple[int, int]:
    """Recompute this month's new/churned customers from two adjacent states."""
    deltas = _effective_deltas(prev)
    churn_mod = 1.0 + deltas["churn_delta_percent"] / 100.0
    churned = 0
    new = 0
    for prev_stream, now_stream in zip(prev.streams, state.streams, strict=True):
        churned_i = min(
            prev_stream.customers,
            round(prev_stream.customers * prev_stream.churn_monthly * churn_mod),
        )
        churned += churned_i
        new += now_stream.customers - prev_stream.customers + churned_i
    return new, churned


def tick(state: BusinessState, rng: random.Random, marketing_spend: float = 0.0) -> BusinessState:
    """Advance one month through the 8-step core loop, returning a new state."""
    month = state.month + 1

    # (1) demand -> new customers / churn
    deltas = _effective_deltas(state)
    signup_mod = 1.0 + deltas["new_signups_delta_percent"] / 100.0
    churn_mod = 1.0 + deltas["churn_delta_percent"] / 100.0
    demand = compute_demand(state.market, month)
    # Spec §5: Revenue = Demand x Price x Market Share x Conversion Rate.
    # Market share follows a logistic adoption curve toward the blueprint's
    # month-12 customer projection: slow start, acceleration, then saturation.
    target = state.streams[0].projected_customers_month_12
    current_customers = sum(s.customers for s in state.streams)
    progress = max(0.0, min(1.0, current_customers / max(1, target)))
    share = 1.0 / (1.0 + math.exp(3.0 * (progress - 0.5)))
    new_total = max(0, round(demand * share * signup_mod))
    churned_total = 0
    for stream in state.streams:
        churned_total += min(
            stream.customers,
            round(stream.customers * stream.churn_monthly * churn_mod),
        )

    # (2) costs
    units_sold = sum(s.customers for s in state.streams)
    costs = compute_costs(state.financials, units_sold, marketing_spend, month)

    # (3)+(4) cash flow + financial state update; per-stream revenue
    streams = []
    revenue = 0.0
    remaining_new = new_total
    for stream in state.streams:
        # v1 allocates all new signups to the first stream (multi-stream
        # weighting is a future refinement)
        allocated_new = remaining_new if stream is state.streams[0] else 0
        churned_i = min(
            stream.customers,
            round(stream.customers * stream.churn_monthly * churn_mod),
        )
        ending, stream_revenue = compute_revenue(allocated_new, churned_i, stream)
        remaining_new -= allocated_new
        revenue += stream_revenue
        streams.append(replace(stream, customers=ending))

    fin = apply_cash_flow(state.financials, revenue, costs["total"])

    new_state = BusinessState(
        month=month,
        financials=fin,
        market=state.market,
        streams=streams,
        triggers_fired=list(state.triggers_fired),
        active_event_effects=list(state.active_event_effects),
        bankrupt=state.bankrupt,
    )

    # (5) trigger checks
    new_state.triggers_fired.extend(check_triggers(new_state))
    if new_state.bankrupt:
        return new_state

    # (6) active event effects (lazy import: T15 contract; no-op until events.py lands)
    try:
        from app.engine.events import apply_due_events

        new_state = apply_due_events(new_state, month)
    except ImportError:
        pass

    # (7) market update
    new_state.market = update_market(new_state.market, rng, month)

    return new_state


def _kpi_snapshot(
    state: BusinessState, new_customers: int, churned_customers: int
) -> dict[str, float]:
    customers = sum(s.customers for s in state.streams)
    burn = state.financials.monthly_burn
    return {
        "cash": round(state.financials.cash, 2),
        "mrr": state.financials.mrr,
        "arr": state.financials.arr,
        "burn": burn,
        "runway": runway_months(state.financials.cash, burn),
        "customers": float(customers),
        "revenue": state.financials.mrr,
        "costs": state.financials.monthly_burn + state.financials.mrr,
        "new_customers": float(new_customers),
        "churned_customers": float(churned_customers),
    }


def run_simulation(
    initial_state: BusinessState,
    months: int,
    seed: int,
    marketing_spend: float = 0.0,
) -> SimulationResult:
    """Run the deterministic loop for ``months`` months with a single seeded RNG."""
    rng = random.Random(seed)
    state = initial_state.snapshot()
    tick_logs: list[TickLog] = []
    month = 0

    for _ in range(months):
        prev = state
        state = tick(state, rng, marketing_spend)
        month += 1
        new_customers, churned_customers = _customer_movement(prev, state)
        kpis = _kpi_snapshot(state, new_customers, churned_customers)
        tick_logs.append(TickLog(month=month, kpis=kpis))
        if state.bankrupt:
            break

    return SimulationResult(
        final_state=state,
        tick_logs=tick_logs,
        triggers=list(state.triggers_fired),
        survived=not state.bankrupt,
        months_simulated=month,
    )
