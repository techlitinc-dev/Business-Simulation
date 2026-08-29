"""Deterministic stress hurdles sourced from an industry pack's hurdle library.

``pack.hurdle_library`` lists the narrative hurdles a pack's users should face
(pack-specific: Churn Spike, Pricing Pressure for SaaS; Supply Chain Delay,
Ad Account Banned for E-commerce). This module turns one library entry into a
valid Format B ``HurdleEvent`` with a mechanical impact plus canned strategic
options, so a stress run on a pack blueprint produces pack-specific events end
to end — including working ``POST /decide`` flow and forward projections.
"""

from __future__ import annotations

from typing import Any

from app.schemas.decision import StrategicOption
from app.schemas.hurdle import (
    HurdleEvent,
    HurdleNarrative,
    ImmediateDeltas,
    MechanicalImpact,
)

#: Per-hurdle-type immediate deltas (deterministic stand-ins for the LLM).
_HURDLE_IMPACTS: dict[str, dict[str, float]] = {
    "churn_spike": {"churn_delta_percent": 100.0},
    "pricing_pressure": {"mrr_delta_percent": -20.0},
    "key_customer_churn": {"mrr_delta_percent": -15.0},
    "sales_slowdown": {"new_signups_delta_percent": -40.0},
    "cac_increase": {"cac_delta_percent": 60.0},
    "integration_outage": {"churn_delta_percent": 10.0},
    "competitor_freemium": {"new_signups_delta_percent": -30.0},
    "viral_growth": {"new_signups_delta_percent": 200.0},
    "enterprise_deal": {"mrr_delta_percent": 30.0},
    "nrr_improvement": {"mrr_delta_percent": 10.0},
    "supply_chain_delay": {"mrr_delta_percent": -15.0},
    "ad_account_banned": {"new_signups_delta_percent": -50.0},
    "q4_surge": {"mrr_delta_percent": 300.0},
    "return_rate_spike": {"mrr_delta_percent": -25.0},
    "competitor_discount": {"mrr_delta_percent": -30.0},
    "influencer_collab": {"new_signups_delta_percent": 100.0},
    "marketplace_delisting": {"mrr_delta_percent": -50.0},
    "inventory_stockout": {"mrr_delta_percent": -25.0},
    "subscription_launch": {"mrr_delta_percent": 15.0},
}

_DEFAULT_IMPACT: dict[str, float] = {"mrr_delta_percent": -10.0}

#: Hurdle type -> Format B category (only the five valid literals). Defaults to
#: "market" when the type isn't listed.
_CATEGORY_OVERRIDES: dict[str, str] = {
    "churn_spike": "market",
    "key_customer_churn": "market",
    "cac_increase": "operational",
    "integration_outage": "operational",
    "enterprise_deal": "financial",
    "nrr_improvement": "financial",
    "subscription_launch": "financial",
}


def _impact_for(entry: dict[str, Any]) -> dict[str, float]:
    return _HURDLE_IMPACTS.get(str(entry.get("type")), _DEFAULT_IMPACT)


def _category_for(hurdle_type: str) -> str:
    value = _CATEGORY_OVERRIDES.get(hurdle_type, "market")
    if value not in {"market", "operational", "financial", "black_swan", "internal"}:
        return "market"
    return value


def build_pack_hurdle_event(entry: dict[str, Any], *, month: int) -> HurdleEvent:
    """Construct a Format B hurdle from one pack library entry (deterministic)."""
    hurdle_type = str(entry.get("type") or "market")
    title = str(entry.get("title") or hurdle_type)
    description = str(entry.get("description") or title)

    return HurdleEvent(
        event_id=f"pack-{hurdle_type}-m{month}",
        trigger_timing=f"month_{month}",
        category=_category_for(hurdle_type),  # type: ignore[arg-type]
        narrative=HurdleNarrative(
            title=title,
            story=description,
            source_actor=_category_for(hurdle_type).title(),
            believability_score=0.8,
        ),
        mechanical_impact=MechanicalImpact(
            immediate=ImmediateDeltas(**_impact_for(entry)),
        ),
        ai_game_master_note=description,
    )


def build_pack_strategic_options(entry: dict[str, Any]) -> list[StrategicOption]:
    """Three deterministic strategic options for a pack hurdle."""
    hurdle_type = str(entry.get("type") or "hurdle")
    title = str(entry.get("title") or hurdle_type)
    return [
        StrategicOption(
            option_id=f"{hurdle_type}-hold",
            name="Hold the course",
            description=f"Absorb the impact of “{title}” and keep current strategy.",
            cash_impact_monthly=0.0,
            probability_success=0.5,
            second_order_risk="No mitigation — the full impact hits the books.",
            required_execution="No change; ride it out.",
        ),
        StrategicOption(
            option_id=f"{hurdle_type}-cut",
            name="Cut costs",
            description=f"Trim non-essential spend to shore up the runway against “{title}”.",
            cash_impact_monthly=1500.0,
            probability_success=0.7,
            second_order_risk="Slower growth while spending is reduced.",
            required_execution="Trim discretionary budget this quarter.",
        ),
        StrategicOption(
            option_id=f"{hurdle_type}-invest",
            name="Invest defensively",
            description=f"Spend to soften “{title}” and protect key revenue.",
            cash_impact_monthly=-2000.0,
            probability_success=0.6,
            second_order_risk="Burns cash faster if the gamble fails.",
            required_execution="Reallocate budget toward mitigation this quarter.",
        ),
    ]