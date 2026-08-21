"""E-commerce / DTC pack — pre-tuned for direct-to-consumer businesses."""

from app.services.industry_packs.pack_registry import IndustryPack, register_pack

ECOMMERCE_PACK = IndustryPack(
    id="ecommerce",
    name="E-commerce / DTC Pack",
    description="Pre-tuned parameters for direct-to-consumer e-commerce businesses.",
    engine_params={
        "monthly_churn": 0.20,
        "cac": 35,
        "ltv_multiplier": 2.5,
        "seasonality_amplitude": 0.30,  # High Q4 seasonality
        "price_elasticity": -1.5,
    },
    blueprint_template={
        "business_type": "ecommerce",
        "pricing_model": "one-time",
        "pricing": {"average_order_value": 75, "repeat_purchase_rate": 0.30},
        "customers": {"initial": 50, "monthly_growth_target": 0.10},
        "financials": {
            "starting_capital": 80000,
            "fixed_monthly_costs": 8000,
            "cogs_pct": 0.40,
        },
        "market": {"tam": 200000, "initial_penetration": 0.00025},
    },
    hurdle_library=[
        {
            "type": "supply_chain_delay",
            "title": "Supply Chain Delay",
            "description": "Supplier delays shipment by 6 weeks",
        },
        {
            "type": "ad_account_banned",
            "title": "Ad Account Banned",
            "description": "Facebook ad account suspended for 2 weeks",
        },
        {
            "type": "q4_surge",
            "title": "Holiday Surge",
            "description": "Q4 drives 4x normal sales volume — fulfillment stress",
        },
        {
            "type": "return_rate_spike",
            "title": "Return Rate Spike",
            "description": "Defective batch causes 25% return rate",
        },
        {
            "type": "competitor_discount",
            "title": "Competitor Discount War",
            "description": "Major competitor drops prices 30%",
        },
        {
            "type": "influencer_collab",
            "title": "Influencer Partnership",
            "description": "Mega influencer post drives 2x traffic",
        },
        {
            "type": "marketplace_delisting",
            "title": "Marketplace Delisting",
            "description": "Amazon removes listing for policy violation",
        },
        {
            "type": "cac_increase",
            "title": "Rising Ad Costs",
            "description": "CPM increases 50% during busy season",
        },
        {
            "type": "inventory_stockout",
            "title": "Inventory Stockout",
            "description": "Best-seller out of stock for 3 weeks",
        },
        {
            "type": "subscription_launch",
            "title": "Subscription Box Launch",
            "description": "Launch subscription tier — reduces churn",
        },
    ],
    vertical_kpis=[
        "average_order_value",
        "repeat_purchase_rate",
        "cogs_pct",
        "inventory_turns",
    ],
)

register_pack(ECOMMERCE_PACK)
