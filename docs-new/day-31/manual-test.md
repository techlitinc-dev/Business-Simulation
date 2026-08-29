# Day 31 — Manual Test Checklist

## Checklist

### 1. List packs
```bash
curl "http://localhost:8000/api/v1/industry-packs/" -H "Authorization: Bearer <token>"
```
- [ ] Both SaaS and E-commerce packs listed

### 2. Get SaaS pack details
```bash
curl "http://localhost:8000/api/v1/industry-packs/saas" -H "Authorization: Bearer <token>"
```
- [ ] 10 hurdles in hurdle_library
- [ ] engine_params has monthly_churn, cac, seasonality_amplitude
- [ ] vertical_kpis includes "mrr" and "churn_rate"

### 3. Use pack in onboarding
- [ ] Navigate to onboarding wizard
- [ ] "Select Industry Pack" step appears
- [ ] Click "SaaS Pack" card → blueprint template fields pre-fill
- [ ] Monthly price defaults to $99, starting_capital to $150,000

### 4. Verify pack hurdles load in simulation
- [ ] Create blueprint from SaaS template
- [ ] Run a stress-test simulation
- [ ] Event feed shows SaaS-specific hurdle events (Churn Spike, Pricing Pressure, etc.)

### 5. Unknown pack
```bash
curl "http://localhost:8000/api/v1/industry-packs/restaurant" -H "Authorization: Bearer <token>"
```
- [ ] Returns 404

### 6. Run pytest
```bash
cd backend && pytest tests/unit/industry_packs/ -v
```
- [ ] 6 passed
