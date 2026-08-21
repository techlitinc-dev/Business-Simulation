"""SaaS pack — pre-tuned parameters for B2B and B2C SaaS businesses."""

from app.services.industry_packs.pack_registry import IndustryPack, register_pack

SAAS_PACK = IndustryPack(
    id="saas",
    name="SaaS Pack",
    description="Pre-tuned parameters for B2B and B2C SaaS businesses.",
    engine_params={
        "monthly_churn": 0.03,
        "cac": 800,
        "ltv_multiplier": 3.0,
        "seasonality_amplitude": 0.05,
        "price_elasticity": -0.8,
    },
    blueprint_template={
        "business_type": "saas",
        "pricing_model": "subscription",
        "pricing": {"monthly_price": 99, "annual_discount": 0.20},
        "customers": {"initial": 10, "monthly_growth_target": 0.15},
        "financials": {
            "starting_capital": 150000,
            "fixed_monthly_costs": 18000,
            "variable_cost_per_customer": 12,
        },
        "market": {"tam": 50000, "initial_penetration": 0.0002},
    },
    hurdle_library=[
        {
            "type": "churn_spike",
            "title": "Churn Spike",
            "description": "Churn doubles for 2 months due to competitor launch",
        },
        {
            "type": "pricing_pressure",
            "title": "Pricing Pressure",
            "description": "Market price drops 20%",
        },
        {
            "type": "key_customer_churn",
            "title": "Key Customer Lost",
            "description": "Top customer cancels — lose 15% of MRR",
        },
        {
            "type": "sales_slowdown",
            "title": "Sales Slowdown",
            "description": "New sales drop 40% for one quarter",
        },
        {
            "type": "cac_increase",
            "title": "CAC Increase",
            "description": "Ad costs double — CAC rises 60%",
        },
        {
            "type": "integration_outage",
            "title": "Integration Outage",
            "description": "Key API partner goes down — 10% churn risk",
        },
        {
            "type": "competitor_freemium",
            "title": "Competitor Freemium",
            "description": "Competitor launches free tier",
        },
        {
            "type": "viral_growth",
            "title": "Viral Growth",
            "description": "Product Hunt launch — 3x signups for 1 month",
        },
        {
            "type": "enterprise_deal",
            "title": "Enterprise Deal",
            "description": "Land a $50K ARR enterprise contract",
        },
        {
            "type": "nrr_improvement",
            "title": "Expansion Revenue",
            "description": "Upsells drive NRR to 110%",
        },
    ],
    vertical_kpis=["mrr", "nrr", "ltv_cac_ratio", "churn_rate", "cac_payback_months"],
)

register_pack(SAAS_PACK)
