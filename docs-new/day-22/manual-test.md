# Day 22 — Manual Test Checklist

## Checklist

### 1. Generate investment teaser PDF
```bash
curl -X POST "http://localhost:8000/api/v1/investor/runs/<run_id>/teaser" \
  -H "Authorization: Bearer <token>" -H "X-Workspace-Id: <ws_id>" -o teaser.pdf
```
- [ ] teaser.pdf downloaded
- [ ] Open PDF: 1-page teaser with Problem, Solution, Key Metrics sections
- [ ] All numbers match the actual simulation run data

### 2. Generate pitch deck outline
```bash
curl -X POST "http://localhost:8000/api/v1/investor/runs/<run_id>/pitch-deck" \
  -H "Authorization: Bearer <token>" -H "X-Workspace-Id: <ws_id>" -o pitch.pdf
```
- [ ] PDF downloaded with 10-12 slides listed
- [ ] Each slide has title + talking points
- [ ] At least one slide references actual simulation numbers

### 3. Verify numbers are grounded
- [ ] Find a number in the teaser PDF (e.g. survival rate)
- [ ] Confirm it matches the run's actual MC results

### 4. Run pytest
```bash
cd backend && pytest tests/unit/agents/test_investor_tools.py -v
```
- [ ] 5 passed
