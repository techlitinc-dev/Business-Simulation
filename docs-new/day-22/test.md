# Day 22 — Test Specification

## Test File
`backend/tests/unit/agents/test_investor_tools.py`

## Test Cases
1. `test_generate_teaser_returns_teaser` — MockProvider returns InvestmentTeaser with problem, simulated_survival, ≥3 key_metrics
2. `test_generate_pitch_outline_has_10_plus_slides` — ≥10 slides returned
3. `test_teaser_to_pdf_returns_bytes` — PDF bytes returned, len>100
4. `test_pitch_slides_have_talking_points` — every slide has ≥1 talking point
5. `test_teaser_endpoint_returns_pdf` — POST /investor/runs/{run_id}/teaser → 200 application/pdf

## Run Commands
```bash
cd backend && pytest tests/unit/agents/test_investor_tools.py -v
```

## Expected
```
5 passed
```
