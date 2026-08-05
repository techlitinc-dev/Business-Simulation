"""KPI snapshots and the resilience score (spec §5 step 8, §9 survival threshold).

Pure engine math — no I/O, no LLM. The monthly KPI dict produced here is the
canonical shape stored in ``TickLog.kpis`` (JSONB) and streamed over WebSocket.
"""

from __future__ import annotations

from app.engine.financials import ltv, runway_months
from app.engine.state import BusinessState


def kpi_snapshot(
    state: BusinessState, new_customers: int, churned_customers: int
) -> dict[str, float]:
    """Build the shared per-month KPI dict from engine state."""
    customers = sum(s.customers for s in state.streams)
    fin = state.financials
    burn = fin.monthly_burn
    first = state.streams[0] if state.streams else None

    churn_rate = first.churn_monthly if first else 0.0
    cac = first.cac if first else 0.0
    ltv_value = (
        ltv(first.price_point, fin.gross_margin, first.churn_monthly)
        if first and first.churn_monthly > 0
        else 0.0
    )
    ratio = ltv_value / cac if cac > 0 else 0.0

    runway = runway_months(fin.cash, burn)
    # JSON-safe: an "infinite" runway (burn <= 0) reads as 0.0, matching the
    # strategist's projection convention.
    runway_value = round(runway, 1) if runway != float("inf") else 0.0

    return {
        "month": float(state.month),
        "cash_balance": round(fin.cash, 2),
        "burn_rate": round(burn, 2),
        "runway_months": runway_value,
        "revenue": round(fin.mrr, 2),
        "costs": round(burn + fin.mrr, 2),
        "net_income": round(fin.mrr - (burn + fin.mrr), 2),
        "mrr": round(fin.mrr, 2),
        "arr": round(fin.arr, 2),
        "customers": float(customers),
        "churn_rate": round(churn_rate, 3),
        "cac": round(cac, 2),
        "ltv": round(ltv_value, 2),
        "ltv_cac_ratio": round(ratio, 2),
        "new_customers": float(new_customers),
        "churned_customers": float(churned_customers),
    }


def resilience_score(state: BusinessState, survival_months: int, total_months: int) -> int:
    """0-100 heuristic: survival share, final cash buffer, runway health."""
    if total_months <= 0:
        total_months = 1
    survival_share = survival_months / total_months
    fin = state.financials
    burn = fin.monthly_burn
    runway = runway_months(fin.cash, burn) if burn > 0 else float("inf")
    if burn > 0 and runway < 1.0:
        runway_component = 0.0
    elif burn > 0 and runway < 3.0:
        runway_component = 0.25
    elif burn > 0 and runway < 6.0:
        runway_component = 0.5
    elif burn > 0 and runway < 12.0:
        runway_component = 0.75
    else:
        runway_component = 1.0
    score = (survival_share * 70.0) + (runway_component * 30.0)
    return int(round(max(0.0, min(100.0, score))))
