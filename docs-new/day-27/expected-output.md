# Day 27 — Expected Output

## Files Created
```
backend/app/api/v1/endpoints/sso.py
backend/app/api/v1/endpoints/scim.py
backend/app/services/scim/__init__.py
backend/app/services/scim/schemas.py
backend/app/services/scim/scim_service.py
backend/tests/integration/test_scim_api.py
```

## SCIM API
- POST /api/v1/scim/v2/Users → 201 ScimUserResponse
- PATCH /api/v1/scim/v2/Users/{id} → 200
- DELETE /api/v1/scim/v2/Users/{id} → 204

## OIDC
- GET /api/v1/sso/oidc/callback → stub 200
- POST /api/v1/sso/oidc/exchange → JWT token

## Note
Production IdP wiring requires OIDC_CLIENT_ID and OIDC_CLIENT_SECRET env vars. These stubs work end-to-end with mock requests for testing. No external IdP required for dev.

## Pytest: 5 passed
