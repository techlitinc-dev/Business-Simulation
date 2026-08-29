# Day 18 — Manual Test Checklist

## Checklist

### 1. Ask a grounded question
```bash
curl -X POST "http://localhost:8000/api/v1/simulations/<run_id>/chat" \
  -H "Authorization: Bearer <token>" -H "X-Workspace-Id: <ws_id>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What was the cash balance in month 6?"}'
```
- [ ] Response has `answer` with a month 6 cash figure
- [ ] `grounded: true`
- [ ] `flagged_claims: []`

### 2. Ask a knowledge question (should say it doesn't know)
```bash
-d '{"question": "What are the current market interest rates?"}'
```
- [ ] Answer says "The simulation data doesn't contain enough information..."

### 3. Verify grounding with a fabricated number
- [ ] Inject a mock answer containing "999999"
- [ ] `grounded: false`, `flagged_claims: ["999999"]`

### 4. Run pytest
```bash
cd backend && pytest tests/unit/copilot/ -v
```
- [ ] 5 passed
