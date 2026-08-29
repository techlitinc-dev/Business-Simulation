# Day 25 — Expected Output

## Files Created
```
backend/app/models/portfolio.py
backend/app/services/portfolio/__init__.py
backend/app/services/portfolio/schemas.py
backend/app/services/portfolio/portfolio_service.py
backend/alembic/versions/i0j1k2l3m4n5_portfolio_tables.py
backend/tests/unit/portfolio/__init__.py
backend/tests/unit/portfolio/test_portfolio_service.py
```

## Sample PortfolioSummary
```json
{
  "portfolio_id": "pf_abc",
  "name": "Acme Ventures Portfolio",
  "member_count": 3,
  "avg_resilience_score": 61.3,
  "workspaces": [
    {"workspace_id": "ws_001", "label": "TechCorp", "resilience_score": 74.2, "survival_rate": 0.78, "drift_alert": false},
    {"workspace_id": "ws_002", "label": "HealthAI", "resilience_score": 58.1, "survival_rate": 0.62, "drift_alert": true},
    {"workspace_id": "ws_003", "label": "EcoShop", "resilience_score": 51.6, "survival_rate": 0.48, "drift_alert": false}
  ]
}
```

## Migration: Clean up/down/up
```
Running upgrade h9i0j1k2l3m4 -> i0j1k2l3m4n5, add portfolio tables
```

## Pytest: 5 passed
