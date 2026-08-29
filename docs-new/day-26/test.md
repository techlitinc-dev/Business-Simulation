# Day 26 — Test Specification

## Tests
- Backend: `tests/integration/test_portfolio_api.py` — CRUD + summary endpoints
- Frontend: build + lint

## Test Cases
1. `test_create_portfolio_returns_201` — POST /portfolios → 201 with portfolio_id
2. `test_add_workspace_to_portfolio` — POST /portfolios/{id}/workspaces → 201
3. `test_get_portfolio_summary` — GET /portfolios/{id}/summary → workspaces sorted by score
4. `test_portfolio_not_found_returns_404` — unknown id → 404
5. `test_cohort_rankings_renders_sorted_list` — CohortRankings shows #1 highest score
6. `test_cohort_rankings_anonymize_toggle` — clicking Anonymize hides real names

## Run Commands
```bash
cd backend && pytest tests/integration/test_portfolio_api.py -v
cd frontend && npm run build
```

## Expected
```
Tests: 4 passing
Build: 0 errors
```
