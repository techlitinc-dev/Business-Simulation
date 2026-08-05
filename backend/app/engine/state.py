"""Engine state model and the blueprint -> state compiler.

The engine is intentionally dependency-free: stdlib ``dataclasses`` only.
No web framework, ORM, schema library, app modules, or I/O of any kind.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Trigger(StrEnum):
    """The four trigger events the monthly loop can fire."""

    BANKRUPTCY = "bankruptcy"
    PROFITABILITY = "profitability"
    FUNDING_NEED = "funding_need"
    MILESTONE = "milestone"


@dataclass
class TeamMember:
    """A single hired team member (payroll is salary_annual / 12 once hired)."""

    role: str
    salary_annual: float
    hire_month: int


@dataclass
class RevenueStream:
    """One revenue line in the blueprint's revenue engine."""

    name: str
    pricing_model: str
    price_point: float
    projected_customers_month_12: int
    ltv: float
    cac: float
    churn_monthly: float
    customers: int = 0


@dataclass
class FinancialState:
    """Cash, revenue, and cost figures for the business."""

    cash: float
    mrr: float
    arr: float
    monthly_burn: float
    fixed_monthly: float
    variable_per_unit: float
    ar_days: int
    ap_days: int
    gross_margin: float
    team: list[TeamMember]
    accounts_receivable: float = 0.0
    accounts_payable: float = 0.0
    profitable_streak: int = 0


@dataclass
class MarketState:
    """Market-level dynamics: size, share, demand, pricing, seasonality."""

    market_size: int
    market_share: float
    base_demand: float
    price: float
    reference_price: float
    price_elasticity: float
    seasonality: list[float]
    competitor_pressure: float
    brand_sentiment: float = 0.5


@dataclass
class TriggerEvent:
    """A trigger that fired during the run."""

    month: int
    trigger: str
    detail: str


@dataclass
class BusinessState:
    """The full in-memory state of one simulated business."""

    month: int
    financials: FinancialState
    market: MarketState
    streams: list[RevenueStream]
    triggers_fired: list[TriggerEvent] = field(default_factory=list)
    active_event_effects: list[dict[str, Any]] = field(default_factory=list)
    bankrupt: bool = False

    def snapshot(self) -> BusinessState:
        """Return an independent deep copy for logging / Monte Carlo branching."""
        return copy.deepcopy(self)


def _require(payload: dict[str, Any], *keys: str, section: str = "") -> None:
    """Raise ValueError naming the first missing key at the given level."""
    for key in keys:
        if key not in payload:
            where = f"{section}.{key}" if section else key
            raise ValueError(f"missing required key: '{where}'")


def compile_blueprint(payload: dict[str, Any]) -> BusinessState:
    """Compile a Format-A blueprint payload into an initial BusinessState (month 0)."""
    _require(payload, "revenue_engine", "cost_structure", "financials")
    revenue_engine = payload["revenue_engine"]
    cost_structure = payload["cost_structure"]
    financials = payload["financials"]

    _require(revenue_engine, "streams", section="revenue_engine")
    streams_raw = revenue_engine["streams"]
    if not streams_raw:
        raise ValueError("missing required key: 'revenue_engine.streams' (must be non-empty)")
    _require(financials, "starting_capital", section="financials")

    streams: list[RevenueStream] = []
    for raw in streams_raw:
        streams.append(
            RevenueStream(
                name=raw["name"],
                pricing_model=raw.get("pricing_model", "Subscription"),
                price_point=float(raw["price_point"]),
                projected_customers_month_12=int(raw["projected_customers_month_12"]),
                ltv=float(raw.get("ltv", 0.0)),
                cac=float(raw.get("cac", 0.0)),
                churn_monthly=float(raw.get("churn_monthly", 0.0)),
            )
        )

    team = [
        TeamMember(
            role=member["role"],
            salary_annual=float(member["salary_annual"]),
            hire_month=int(member.get("hire_month", 0)),
        )
        for member in cost_structure.get("team", [])
    ]

    sim_params = payload.get("simulation_parameters", {}) or {}
    projected_m12 = streams[0].projected_customers_month_12

    financial = FinancialState(
        cash=float(financials["starting_capital"]),
        mrr=0.0,
        arr=0.0,
        monthly_burn=float(cost_structure.get("burn_rate_month_1", 0.0)),
        fixed_monthly=float(cost_structure.get("fixed_monthly", 0.0)),
        variable_per_unit=float(cost_structure.get("variable_per_unit", 0.0)),
        ar_days=int(financials.get("ar_days", 30)),
        ap_days=int(financials.get("ap_days", 30)),
        gross_margin=float(financials.get("gross_margin", 0.8)),
        team=team,
    )

    seasonality = sim_params.get("seasonality")
    if seasonality is None:
        seasonality = [1.0] * 12
    seasonality = [float(s) for s in seasonality]
    if len(seasonality) != 12:
        raise ValueError(f"market.seasonality must have exactly 12 entries, got {len(seasonality)}")

    market = MarketState(
        market_size=int(sim_params.get("market_size", projected_m12 * 100)),
        market_share=float(sim_params.get("market_share", 0.0)),
        base_demand=float(sim_params.get("base_demand", projected_m12 / 12)),
        price=float(streams[0].price_point),
        reference_price=float(streams[0].price_point),
        price_elasticity=float(sim_params.get("price_elasticity", -1.5)),
        seasonality=seasonality,
        competitor_pressure=float(sim_params.get("competitor_pressure", 0.0)),
        brand_sentiment=float(sim_params.get("brand_sentiment", 0.5)),
    )

    return BusinessState(
        month=0,
        financials=financial,
        market=market,
        streams=streams,
    )
