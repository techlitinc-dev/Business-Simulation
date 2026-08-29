# Day 31 — Test Specification

## Test File
`backend/tests/unit/industry_packs/test_pack_registry.py`

## Test Cases
1. `test_saas_pack_registered` — get_pack("saas") returns SaaS Pack with 10 hurdles
2. `test_ecommerce_pack_registered` — get_pack("ecommerce") returns pack with 10 hurdles
3. `test_list_packs_returns_both` — both "saas" and "ecommerce" in list
4. `test_saas_blueprint_template_has_required_fields` — financials.starting_capital present
5. `test_saas_engine_params_have_churn` — monthly_churn < 0.10
6. `test_unknown_pack_returns_none` — get_pack("restaurant") → None

## Run Commands
```bash
cd backend && pytest tests/unit/industry_packs/ -v
```

## Expected
```
6 passed
```
