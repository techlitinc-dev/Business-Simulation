# Day 27 — Test Specification

## Test File
`backend/tests/integration/test_scim_api.py`

## Test Cases
1. `test_scim_provision_user` — POST /scim/v2/Users → 201 with userName and active=true
2. `test_scim_invalid_token` — wrong token → 401
3. `test_scim_deprovision_user` — DELETE → 204, user deactivated
4. `test_oidc_callback_returns_200` — GET /sso/oidc/callback → 200 stub response
5. `test_oidc_exchange_creates_user` — POST /sso/oidc/exchange → access_token returned

## Run Commands
```bash
cd backend && pytest tests/integration/test_scim_api.py -v
cd backend && ruff check app/api/v1/endpoints/sso.py app/services/scim/
```

## Expected
```
5 passed
```
