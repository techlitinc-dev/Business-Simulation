# Day 25 — Test Specification

## Test File
`backend/tests/unit/portfolio/test_portfolio_service.py`

## Test Cases
1. `test_get_portfolio_summary_returns_none_for_unknown` — unknown portfolio_id → None
2. `test_get_portfolio_summary_sorts_by_score` — workspaces sorted highest score first
3. `test_create_portfolio_persists_record` — creates Portfolio row with correct owner
4. `test_add_workspace_creates_membership` — PortfolioMembership row created
5. `test_remove_workspace_deletes_membership` — membership deleted, workspace data unchanged

## Run Commands
```bash
cd backend && pytest tests/unit/portfolio/ -v
cd backend && alembic upgrade head
```

## Expected
```
5 passed
Migration clean
```
