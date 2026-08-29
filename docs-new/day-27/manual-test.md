# Day 27 — Manual Test Checklist

## Checklist

### 1. SCIM provision a user
```bash
curl -X POST "http://localhost:8000/api/v1/scim/v2/Users?workspace_id=<ws_id>" \
  -H "Authorization: Bearer changeme-scim-secret" \
  -H "Content-Type: application/json" \
  -d '{"userName":"scimtest@example.com","displayName":"SCIM Test","active":true}'
```
- [ ] 201 response
- [ ] user_id returned
- [ ] User can log in with that email

### 2. SCIM deprovision
```bash
curl -X DELETE "http://localhost:8000/api/v1/scim/v2/Users/<user_id>" \
  -H "Authorization: Bearer changeme-scim-secret"
```
- [ ] 204 response
- [ ] User account deactivated (not deleted)
- [ ] Logging in with deactivated account returns 401

### 3. SCIM invalid token
```bash
curl -X POST ... -H "Authorization: Bearer wrong-token"
```
- [ ] 401 Unauthorized

### 4. OIDC stub
```bash
curl "http://localhost:8000/api/v1/sso/oidc/callback?code=testcode123"
```
- [ ] 200 with stub message

### 5. Run pytest
```bash
cd backend && pytest tests/integration/test_scim_api.py -v
```
- [ ] 5 passed
