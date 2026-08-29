# Day 31 — F-11: Vertical Industry Packs (SaaS + E-commerce)

## Feature
F-11: Vertical Industry Packs

## Goal
Create a registry of industry packs. Implement SaaS and E-commerce packs with pre-tuned engine parameters, blueprint templates, and 10 hurdle libraries each. Wire into onboarding wizard.

---

## Step 1 — Pack Registry

`backend/app/services/industry_packs/__init__.py` — empty

`backend/app/services/industry_packs/pack_registry.py`:
```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IndustryPack:
    id: str
    name: str
    description: str
    engine_params: dict[str, Any]             # parameter overrides applied to blueprint
    blueprint_template: dict[str, Any]        # base blueprint payload
    hurdle_library: list[dict]                # 10 hurdle event templates
    report_manifest_variant: str = "resilience_audit"
    vertical_kpis: list[str] = field(default_factory=list)


PACK_REGISTRY: dict[str, IndustryPack] = {}


def register_pack(pack: IndustryPack):
    PACK_REGISTRY[pack.id] = pack


def get_pack(pack_id: str) -> IndustryPack | None:
    return PACK_REGISTRY.get(pack_id)


def list_packs() -> list[dict]:
    return [{"id": p.id, "name": p.name, "description": p.description} for p in PACK_REGISTRY.values()]
```

---

## Step 2 — SaaS Pack

`backend/app/services/industry_packs/saas_pack.py`:
```python
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
        {"type": "churn_spike", "title": "Churn Spike", "description": "Churn doubles for 2 months due to competitor launch"},
        {"type": "pricing_pressure", "title": "Pricing Pressure", "description": "Market price drops 20%"},
        {"type": "key_customer_churn", "title": "Key Customer Lost", "description": "Top customer cancels — lose 15% of MRR"},
        {"type": "sales_slowdown", "title": "Sales Slowdown", "description": "New sales drop 40% for one quarter"},
        {"type": "cac_increase", "title": "CAC Increase", "description": "Ad costs double — CAC rises 60%"},
        {"type": "integration_outage", "title": "Integration Outage", "description": "Key API partner goes down — 10% churn risk"},
        {"type": "competitor_freemium", "title": "Competitor Freemium", "description": "Competitor launches free tier"},
        {"type": "viral_growth", "title": "Viral Growth", "description": "Product Hunt launch — 3x signups for 1 month"},
        {"type": "enterprise_deal", "title": "Enterprise Deal", "description": "Land a $50K ARR enterprise contract"},
        {"type": "nrr_improvement", "title": "Expansion Revenue", "description": "Upsells drive NRR to 110%"},
    ],
    vertical_kpis=["mrr", "nrr", "ltv_cac_ratio", "churn_rate", "cac_payback_months"],
)

register_pack(SAAS_PACK)
```

---

## Step 3 — E-commerce Pack

`backend/app/services/industry_packs/ecommerce_pack.py`:
```python
from app.services.industry_packs.pack_registry import IndustryPack, register_pack

ECOMMERCE_PACK = IndustryPack(
    id="ecommerce",
    name="E-commerce / DTC Pack",
    description="Pre-tuned parameters for direct-to-consumer e-commerce businesses.",
    engine_params={
        "monthly_churn": 0.20,
        "cac": 35,
        "ltv_multiplier": 2.5,
        "seasonality_amplitude": 0.30,   # High Q4 seasonality
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
        {"type": "supply_chain_delay", "title": "Supply Chain Delay", "description": "Supplier delays shipment by 6 weeks"},
        {"type": "ad_account_banned", "title": "Ad Account Banned", "description": "Facebook ad account suspended for 2 weeks"},
        {"type": "q4_surge", "title": "Holiday Surge", "description": "Q4 drives 4x normal sales volume — fulfillment stress"},
        {"type": "return_rate_spike", "title": "Return Rate Spike", "description": "Defective batch causes 25% return rate"},
        {"type": "competitor_discount", "title": "Competitor Discount War", "description": "Major competitor drops prices 30%"},
        {"type": "influencer_collab", "title": "Influencer Partnership", "description": "Mega influencer post drives 2x traffic"},
        {"type": "marketplace_delisting", "title": "Marketplace Delisting", "description": "Amazon removes listing for policy violation"},
        {"type": "cac_increase", "title": "Rising Ad Costs", "description": "CPM increases 50% during busy season"},
        {"type": "inventory_stockout", "title": "Inventory Stockout", "description": "Best-seller out of stock for 3 weeks"},
        {"type": "subscription_launch", "title": "Subscription Box Launch", "description": "Launch subscription tier — reduces churn"},
    ],
    vertical_kpis=["average_order_value", "repeat_purchase_rate", "cogs_pct", "inventory_turns"],
)

register_pack(ECOMMERCE_PACK)
```

---

## Step 4 — API endpoint

`backend/app/api/v1/endpoints/industry_packs.py`:
```python
from fastapi import APIRouter, HTTPException
from app.services.industry_packs.pack_registry import list_packs, get_pack
import app.services.industry_packs.saas_pack   # noqa — register packs
import app.services.industry_packs.ecommerce_pack   # noqa

router = APIRouter(prefix="/industry-packs", tags=["industry-packs"])


@router.get("/")
async def list_industry_packs():
    return list_packs()


@router.get("/{pack_id}")
async def get_industry_pack(pack_id: str):
    pack = get_pack(pack_id)
    if not pack:
        raise HTTPException(404, f"Pack '{pack_id}' not found")
    return {
        "id": pack.id, "name": pack.name, "description": pack.description,
        "engine_params": pack.engine_params,
        "hurdle_library": pack.hurdle_library,
        "vertical_kpis": pack.vertical_kpis,
    }
```

---

## Step 5 — Wire into onboarding

In `frontend/src/features/onboarding/` onboarding wizard, add an industry pack selector step:

```typescript
// IndustryPackSelector.tsx
// Fetches GET /industry-packs, shows cards with name + description
// On selection: pre-fills blueprint template in wizard state
```

---

## Step 6 — Tests

`backend/tests/unit/industry_packs/test_pack_registry.py`:
```python
import pytest
import app.services.industry_packs.saas_pack    # noqa — register
import app.services.industry_packs.ecommerce_pack  # noqa
from app.services.industry_packs.pack_registry import get_pack, list_packs

def test_saas_pack_registered():
    pack = get_pack("saas")
    assert pack is not None
    assert pack.name == "SaaS Pack"
    assert len(pack.hurdle_library) == 10

def test_ecommerce_pack_registered():
    pack = get_pack("ecommerce")
    assert pack is not None
    assert len(pack.hurdle_library) == 10

def test_list_packs_returns_both():
    packs = list_packs()
    ids = [p["id"] for p in packs]
    assert "saas" in ids
    assert "ecommerce" in ids

def test_saas_blueprint_template_has_required_fields():
    pack = get_pack("saas")
    assert "starting_capital" in pack.blueprint_template["financials"]
    assert "monthly_price" in pack.blueprint_template["pricing"]

def test_saas_engine_params_have_churn():
    pack = get_pack("saas")
    assert "monthly_churn" in pack.engine_params
    assert pack.engine_params["monthly_churn"] < 0.10

def test_unknown_pack_returns_none():
    assert get_pack("restaurant") is None
```

---

## Verification Commands
```bash
cd backend && pytest tests/unit/industry_packs/ -v
cd backend && ruff check app/services/industry_packs/ app/api/v1/endpoints/industry_packs.py
```
