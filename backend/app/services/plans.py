"""Plan tiers and limits (T40/T41) — single source of truth for pricing.

A limit of ``-1`` means unlimited. ``stripe_price_id`` is resolved from
settings env vars lazily so tests can override settings cheaply.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core import config


@dataclass(frozen=True)
class Plan:
    id: str
    stripe_price_id: str | None
    price_usd: int
    runs_per_month: int
    monte_carlo_runs_per_batch: int
    llm_tokens_per_month: int
    seats: int


def _resolve_plan_tier() -> dict[str, Plan]:
    """Build the tier registry against current settings (lazy)."""
    settings = config.get_settings()
    return {
        "free": Plan(
            id="free",
            stripe_price_id=None,
            price_usd=0,
            runs_per_month=-1,
            monte_carlo_runs_per_batch=25,
            llm_tokens_per_month=50_000,
            seats=1,
        ),
        "pro": Plan(
            id="pro",
            stripe_price_id=settings.stripe_price_pro_monthly,
            price_usd=49,
            runs_per_month=50,
            monte_carlo_runs_per_batch=500,
            llm_tokens_per_month=2_000_000,
            seats=5,
        ),
        "enterprise": Plan(
            id="enterprise",
            stripe_price_id=settings.stripe_price_enterprise_monthly,
            price_usd=499,
            runs_per_month=-1,
            monte_carlo_runs_per_batch=-1,
            llm_tokens_per_month=-1,
            seats=-1,
        ),
    }


def get_plans() -> dict[str, Plan]:
    """Return the plan registry, resolved against current settings."""
    return _resolve_plan_tier()


def get_plan(tier: str) -> Plan:
    plans = _resolve_plan_tier()
    if tier not in plans:
        raise ValueError(f"Unknown tier: {tier}")
    return plans[tier]
