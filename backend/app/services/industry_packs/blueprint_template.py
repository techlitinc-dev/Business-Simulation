"""Build a canonical Format A blueprint from an industry pack's template.

The pack keeps a human-friendly ``blueprint_template`` (business_type, pricing,
customers, financials) plus pre-tuned ``engine_params`` (churn, CAC, LTV, ...).
This module folds those onto the full ``BlueprintPayload`` contract so a pack can
pre-fill a real blueprint — the mechanism behind "create a blueprint from the
SaaS/E-commerce template".
"""

from __future__ import annotations

from collections.abc import Mapping

from app.schemas.blueprint import (
    BlueprintPayload,
    BusinessProfile,
    CostStructure,
    Financials,
    RevenueEngine,
    RevenueStream,
    SimulationParameters,
)
from app.services.industry_packs.pack_registry import IndustryPack

DEFAULT_STAGE = "Pre-Seed"
DEFAULT_TARGET_RUNWAY_MONTHS = 12
DEFAULT_GEOGRAPHY = "Global"


def _first(mapping: Mapping[str, object], *keys: str) -> Mapping[str, object]:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def _as_float(mapping: Mapping[str, object], key: str) -> float:
    try:
        return float(str(mapping.get(key) or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _as_int(mapping: Mapping[str, object], key: str) -> int:
    try:
        return int(str(mapping.get(key) or 0))
    except (TypeError, ValueError):
        return 0


def build_blueprint_from_pack(
    pack: IndustryPack, *, stage: str = DEFAULT_STAGE
) -> BlueprintPayload:
    """Pre-fill a valid ``BlueprintPayload`` from a pack's template + engine params.

    Mappings onto Format A:

    - monthly price -> ``revenue stream.price_point``
    - ``engine_params.monthly_churn`` -> ``stream.churn_monthly``
    - ``engine_params.cac`` -> ``stream.cac``
    - ``ltv = ltv_multiplier * cac`` -> ``stream.ltv``
    - template ``financials.starting_capital`` / ``fixed_monthly_costs`` ->
      blueprint ``financials`` / ``cost_structure``
    """
    template = pack.blueprint_template
    engine = pack.engine_params
    pricing = _first(template, "pricing")
    financial_block = _first(template, "financials")
    customers = _first(template, "customers")

    monthly_price = _as_float(pricing, "monthly_price")
    cac = _as_float(engine, "cac")
    churn = _as_float(engine, "monthly_churn")
    ltv = _as_float(engine, "ltv_multiplier") * cac

    initial = _as_int(customers, "initial")
    growth = _as_float(customers, "monthly_growth_target")
    projected_m12 = max(1, int(round(initial * (1 + growth) ** 12)))

    variable = _as_float(
        financial_block, "variable_cost_per_unit"
    ) or _as_float(financial_block, "cogs_pct")
    fixed_monthly = _as_float(financial_block, "fixed_monthly_costs")
    starting_capital = _as_float(financial_block, "starting_capital")

    return BlueprintPayload(
        blueprint_version="1.0",
        business_profile=BusinessProfile(
            model_type=str(template.get("business_type") or pack.id),
            stage=stage,
            industry=pack.id,
            geography=DEFAULT_GEOGRAPHY,
        ),
        revenue_engine=RevenueEngine(
            streams=[
                RevenueStream(
                    name="Primary",
                    pricing_model=str(
                        template.get("pricing_model") or "subscription"
                    ),
                    price_point=monthly_price if monthly_price > 0 else 1.0,
                    projected_customers_month_12=projected_m12,
                    ltv=ltv,
                    cac=cac,
                    churn_monthly=min(max(churn, 0.0), 1.0),
                )
            ]
        ),
        cost_structure=CostStructure(
            fixed_monthly=fixed_monthly,
            variable_per_unit=variable,
            team=[],
            burn_rate_month_1=fixed_monthly,
        ),
        financials=Financials(
            starting_capital=starting_capital,
            funding_rounds=[],
            target_runway_months=DEFAULT_TARGET_RUNWAY_MONTHS,
        ),
        identified_vulnerabilities=[],
        simulation_parameters=SimulationParameters(),
    )
