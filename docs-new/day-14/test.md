# Day 14 — Test Specification

## Test File
`backend/tests/unit/actuals/test_drift_monitor.py`

## Test Cases
1. `test_should_alert_above_threshold` — score_delta=-6 → should_alert returns True
2. `test_should_not_alert_below_threshold` — score_delta=-3 → should_alert returns False
3. `test_should_not_alert_positive_delta` — score_delta=+2 → should_alert returns False
4. `test_dispatch_alert_calls_notification` — creates notification with "Drift Alert" in title
5. `test_celery_task_importable` — `check_all_blueprints` task is importable with correct name

## Run Commands
```bash
cd backend && pytest tests/unit/actuals/ -v
```

## Expected
```
All actuals tests passing (13 from previous + 5 = 18 total)
```
