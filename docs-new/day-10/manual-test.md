# Day 10 — Manual Test Checklist

## Checklist

### 1. Run a sweep via curl
```bash
curl -X POST http://localhost:8000/api/v1/whatif/sweep \
  -H "Authorization: Bearer <pro_token>" \
  -H "X-Workspace-Id: <workspace_id>" \
  -H "Content-Type: application/json" \
  -d '{"blueprint_id":"<bp_id>","param":"monthly_churn","min_value":0.02,"max_value":0.12,"steps":5,"mc_runs":10}'
```
- [ ] 200 response with 5 grid points
- [ ] survival_rates generally decrease across grid

### 2. Save a version from a grid point
```bash
curl -X POST http://localhost:8000/api/v1/whatif/save-version \
  -H "Authorization: Bearer <pro_token>" \
  -H "X-Workspace-Id: <workspace_id>" \
  -H "Content-Type: application/json" \
  -d '{"blueprint_id":"<bp_id>","param":"monthly_churn","value":0.04,"version_label":"Optimistic Churn"}'
```
- [ ] 201 response with new bpv_ id
- [ ] New version visible in blueprint list (`GET /api/v1/blueprints/<bp_id>`)
- [ ] New version payload has `monthly_churn: 0.04`

### 3. Test free plan rejection
```bash
curl -X POST http://localhost:8000/api/v1/whatif/sweep \
  -H "Authorization: Bearer <free_token>" \
  ...
```
- [ ] 402 response with "Pro plan required" message

### 4. Verify new version can be run
- [ ] Use new version id to start a simulation: `POST /api/v1/simulations`
- [ ] Simulation uses the overridden churn value

### 5. Full test suite
```bash
cd backend && pytest --tb=short -q
```
- [ ] All tests pass
