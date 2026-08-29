# Day 30 — Expected Output

## Files Created
```
backend/app/services/integrations/slack_notifier.py
backend/app/services/integrations/webhook_service.py
backend/app/services/integrations/csv_exporter.py
backend/app/api/v1/endpoints/export.py
frontend/src/features/settings/IntegrationsPage.tsx
backend/tests/unit/integrations/test_csv_exporter.py
```

## CSV Export Format

### ticks.csv
```csv
month,revenue,costs,cash,customers,mrr,runway_months,ltv_cac_ratio,churn_rate
1,12000,14000,86000,8,12000,5.2,1.1,0.05
2,15500,14200,87300,11,15500,5.4,1.3,0.04
...
```

### mc.csv
```csv
metric,value
survival_rate,0.68
median_lifespan,18.0
...

kill_vector_type,frequency
cash_out,0.41
churn_death,0.27
```

## Webhook Payload + Signature Header
```
POST https://example.com/webhook
X-Forge-Event: run.completed
X-Forge-Signature: sha256=a3f9c21b8e4d...
Content-Type: application/json

{"run_id": "...", "survival_rate": 0.68, ...}
```

## Pytest: 6 passed
