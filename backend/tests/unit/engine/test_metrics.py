"""Unit tests for engine metrics (kpi_snapshot + resilience_score)."""

from app.engine.metrics import kpi_snapshot, resilience_score
from app.engine.state import BusinessState, FinancialState, MarketState, RevenueStream


def _state(
    *,
    cash: float = 500_000.0,
    mrr: float = 50_000.0,
    burn: float = 20_000.0,
    customers: int = 500,
    churn: float = 0.05,
    cac: float = 850.0,
    price: float = 99.0,
    gross_margin: float = 0.8,
    month: int = 6,
) -> BusinessState:
    fin = FinancialState(
        cash=cash,
        mrr=mrr,
        arr=mrr * 12,
        monthly_burn=burn,
        fixed_monthly=20_000.0,
        variable_per_unit=0.0,
        ar_days=0,
        ap_days=0,
        gross_margin=gross_margin,
        team=[],
    )
    market = MarketState(
        market_size=100_000,
        market_share=0.01,
        base_demand=1_000,
        price=price,
        reference_price=price,
        price_elasticity=-1.5,
        seasonality=[1.0] * 12,
        competitor_pressure=0.1,
        brand_sentiment=0.5,
    )
    stream = RevenueStream(
        name="SaaS",
        pricing_model="Subscription",
        price_point=price,
        projected_customers_month_12=2_000,
        ltv=1_584.0,
        cac=cac,
        churn_monthly=churn,
        customers=customers,
    )
    return BusinessState(
        month=month, financials=fin, market=market, streams=[stream]
    )


def test_kpi_snapshot_shapes_and_values() -> None:
    state = _state()
    kpis = kpi_snapshot(state, new_customers=10, churned_customers=5)

    assert kpis["month"] == 6.0
    assert kpis["cash_balance"] == 500_000.0
    assert kpis["burn_rate"] == 20_000.0
    assert kpis["customers"] == 500.0
    assert kpis["new_customers"] == 10.0
    assert kpis["churned_customers"] == 5.0
    assert kpis["churn_rate"] == 0.05
    assert kpis["cac"] == 850.0
    # LTV = price * gross_margin / churn = 99*0.8/0.05 = 1584
    assert kpis["ltv"] == 1584.0
    assert kpis["ltv_cac_ratio"] == round(1584 / 850, 2)
    assert kpis["runway_months"] == 25.0
    # net_income = mrr - (burn + mrr) = -burn
    assert kpis["net_income"] == -20_000.0


def test_kpi_snapshot_empty_streams_and_infinite_runway() -> None:
    state = _state(burn=-5_000.0)  # profitable → negative burn
    state.streams = []
    kpis = kpi_snapshot(state, 0, 0)

    assert kpis["runway_months"] == 0.0  # infinite runway reads as 0.0
    assert kpis["churn_rate"] == 0.0
    assert kpis["cac"] == 0.0
    assert kpis["ltv"] == 0.0
    assert kpis["ltv_cac_ratio"] == 0.0
    assert kpis["customers"] == 0.0


def test_kpi_snapshot_zero_churn_ltv_zero() -> None:
    state = _state(churn=0.0)
    kpis = kpi_snapshot(state, 0, 0)
    assert kpis["ltv"] == 0.0
    assert kpis["ltv_cac_ratio"] == 0.0


def test_resilience_score_survived_all_months() -> None:
    state = _state(cash=1_000_000.0, burn=20_000.0)  # runway 50mo
    score = resilience_score(state, survival_months=24, total_months=24)
    assert score == 100


def test_resilience_score_bankrupt_early() -> None:
    state = _state(cash=-100.0, burn=20_000.0)  # runway < 1
    score = resilience_score(state, survival_months=2, total_months=24)
    # survival_share 2/24*70 ≈ 5.8 + 0 runway = ~6
    assert 0 <= score <= 10


def test_resilience_score_runway_bands() -> None:
    # runway 2.5 months → 0.25 component
    s1 = _state(cash=50_000.0, burn=20_000.0)
    r1 = resilience_score(s1, survival_months=12, total_months=24)
    # runway 4 months → 0.5 component
    s2 = _state(cash=80_000.0, burn=20_000.0)
    r2 = resilience_score(s2, survival_months=12, total_months=24)
    # runway 8 months → 0.75 component
    s3 = _state(cash=160_000.0, burn=20_000.0)
    r3 = resilience_score(s3, survival_months=12, total_months=24)
    assert r1 < r2 < r3


def test_resilience_score_total_months_zero_guard() -> None:
    state = _state()
    score = resilience_score(state, survival_months=0, total_months=0)
    assert 0 <= score <= 100


def test_resilience_score_profitable_infinite_runway() -> None:
    state = _state(burn=-10_000.0)  # profitable
    score = resilience_score(state, survival_months=24, total_months=24)
    assert score == 100
