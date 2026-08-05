"""Market dynamics: demand curve, elasticity, seasonality, competitor pressure (spec §5)."""

from __future__ import annotations

import random
from dataclasses import replace

from app.engine.state import MarketState

_COMPETITOR_PRESSURE_MAX = 0.8
_SENTIMENT_MEAN = 0.5
_MARKET_GROWTH_RATE = 0.005


def compute_demand(market: MarketState, month: int) -> float:
    """Demand = base x seasonal x price_factor x pressure x sentiment, clamped."""
    seasonal = market.seasonality[(month - 1) % 12]
    price_factor = (market.price / market.reference_price) ** market.price_elasticity
    pressure = 1.0 - market.competitor_pressure
    sentiment = 0.5 + market.brand_sentiment  # range [0.5, 1.5]
    demand = market.base_demand * seasonal * price_factor * pressure * sentiment
    upper = float(market.market_size)
    return float(max(0.0, min(upper, demand)))


def price_change_effect(market: MarketState, new_price: float) -> MarketState:
    """Return a new MarketState with price = new_price; demand impact via elasticity."""
    return replace(market, price=new_price)


def update_market(market: MarketState, rng: random.Random, month: int) -> MarketState:
    """Spec §5 step 7: deterministic drift plus seeded noise on a new MarketState."""
    pressure = market.competitor_pressure + 0.002 + rng.uniform(-0.005, 0.005)
    pressure = max(0.0, min(_COMPETITOR_PRESSURE_MAX, pressure))
    sentiment = market.brand_sentiment + 0.1 * (_SENTIMENT_MEAN - market.brand_sentiment)
    sentiment += rng.uniform(-0.01, 0.01)
    sentiment = max(0.0, min(1.0, sentiment))
    new_size = int(round(market.market_size * (1 + _MARKET_GROWTH_RATE)))
    return replace(
        market,
        competitor_pressure=pressure,
        brand_sentiment=sentiment,
        market_size=new_size,
    )


def apply_competitor_shock(
    market: MarketState, pressure_delta: float, sentiment_delta: float
) -> MarketState:
    """Apply competitor/sentiment deltas (T15 event injector), clamped, no mutation."""
    pressure = max(0.0, min(_COMPETITOR_PRESSURE_MAX, market.competitor_pressure + pressure_delta))
    sentiment = max(0.0, min(1.0, market.brand_sentiment + sentiment_delta))
    return replace(market, competitor_pressure=pressure, brand_sentiment=sentiment)
