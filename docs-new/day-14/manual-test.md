# Day 14 — Manual Test Checklist

## Checklist

### 1. Manually trigger drift monitor
```bash
cd backend && celery -A app.core.celery_app call workers.drift_monitor.check_all_blueprints
```
- [ ] No error
- [ ] Log shows "Checking N blueprints with actuals"
- [ ] For blueprints with large churn delta in actuals: "Alert triggered"

### 2. Verify notification created
```sql
SELECT * FROM notifications WHERE notification_type = 'drift_alert' ORDER BY created_at DESC LIMIT 5;
```
- [ ] Notification row exists with correct title and body

### 3. Check email mock log
- [ ] Console email log (if SMTP not configured) shows the email content
- [ ] Subject: "[Forge] Drift Alert — <workspace name>"

### 4. Test threshold boundary
```python
from app.services.actuals.alert_service import should_alert
from app.services.actuals.variance import VarianceDelta
import asyncio

# Exactly at threshold — should NOT alert (strictly less than -threshold)
delta_at_threshold = VarianceDelta(blueprint_id="x", month=1,
    prior_survival_rate=0.7, new_survival_rate=0.6, survival_delta=-0.1,
    prior_runway_median=18, new_runway_median=16, runway_delta=-2,
    prior_resilience_score=65, new_resilience_score=60, score_delta=-5.0,
    key_changes=[])
print(asyncio.run(should_alert(delta_at_threshold)))  # False (= not <)
```
- [ ] Returns False at exactly 5.0 threshold

### 5. Celery-beat schedule shows in list
```bash
cd backend && celery -A app.core.celery_app beat --dry-run 2>&1 | grep drift
```
- [ ] "drift-monitor-daily" appears in schedule output
