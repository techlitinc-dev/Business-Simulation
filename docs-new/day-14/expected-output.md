# Day 14 — Expected Output

## Files Created
```
backend/app/services/actuals/alert_service.py
backend/app/workers/drift_monitor.py
backend/tests/unit/actuals/test_drift_monitor.py
```

## Files Modified
```
backend/app/core/celery_app.py  — beat_schedule entry added
```

## Celery-Beat Schedule
```
drift-monitor-daily: crontab(hour=7, minute=0) → workers.drift_monitor.check_all_blueprints
```

## Sample Notification Created
```json
{
  "title": "📉 Resilience Score Drift Alert",
  "body": "Drift Alert: Your resilience score dropped 14.3 points (from 68.4 to 54.1) after importing Month 3 actuals. Primary driver: monthly_churn increased from 0.05 to 0.08.",
  "link": "/blueprints/bp_abc/actuals",
  "notification_type": "drift_alert"
}
```

## Sample Email
```
Subject: [Forge] Drift Alert — Acme Corp
Body: Drift Alert: Your resilience score dropped...
      View full report: /blueprints/bp_abc/actuals
```

## Manual Trigger Log
```
$ celery call workers.drift_monitor.check_all_blueprints
[INFO] [drift_monitor] Checking 3 blueprints with actuals
[INFO] [drift_monitor] Alert triggered for bp_abc: score_delta=-14.3
[DEBUG] [drift_monitor] No alert for bp_xyz: score_delta=-2.1
```

## Pytest: 18 total passing
