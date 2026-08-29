# Day 31 — Expected Output

## Files Created
```
backend/app/services/industry_packs/__init__.py
backend/app/services/industry_packs/pack_registry.py
backend/app/services/industry_packs/saas_pack.py
backend/app/services/industry_packs/ecommerce_pack.py
backend/app/api/v1/endpoints/industry_packs.py
backend/tests/unit/industry_packs/__init__.py
backend/tests/unit/industry_packs/test_pack_registry.py
frontend/src/features/onboarding/IndustryPackSelector.tsx
```

## GET /api/v1/industry-packs/
```json
[
  {"id": "saas", "name": "SaaS Pack", "description": "Pre-tuned parameters for B2B and B2C SaaS businesses."},
  {"id": "ecommerce", "name": "E-commerce / DTC Pack", "description": "Pre-tuned parameters for DTC e-commerce."}
]
```

## GET /api/v1/industry-packs/saas
```json
{
  "id": "saas",
  "name": "SaaS Pack",
  "engine_params": {"monthly_churn": 0.03, "cac": 800, ...},
  "hurdle_library": [{"type": "churn_spike", "title": "Churn Spike", ...}, ...],
  "vertical_kpis": ["mrr", "nrr", "ltv_cac_ratio", ...]
}
```

## Onboarding
- Select "SaaS Pack" → blueprint wizard pre-fills with SaaS template values
- Hurdle library for the run is loaded from the pack's 10 hurdles

## Pytest: 6 passed
