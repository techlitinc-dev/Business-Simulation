# Day 14 — F-04: Drift Alerts (Celery-Beat + Email/Notification)

## Feature
F-04: Living Blueprint & Plan-vs-Actuals

## Goal
Implement a Celery-beat periodic task that re-simulates each blueprint with actuals, compares resilience score to the last run, and triggers an alert if score drops more than the threshold.

## Prerequisites
- Day 12–13 complete
- `celery_beat` configured in Celery app
- Existing notification service (T37) and email abstraction (T10)

---

## Step 1 — Create `backend/app/services/actuals/alert_service.py`

```python
from __future__ import annotations
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.actuals.variance import VarianceDelta

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 5.0   # pp drop in resilience score


async def should_alert(delta: VarianceDelta, threshold: float = DEFAULT_THRESHOLD) -> bool:
    return delta.score_delta <= -threshold


async def dispatch_drift_alert(
    delta: VarianceDelta,
    workspace_id: str,
    db: AsyncSession,
):
    """Send notification + email when resilience score drops past threshold."""
    from app.services.workspace_service import get_workspace
    workspace = await get_workspace(workspace_id, db)

    message = (
        f"Drift Alert: Your resilience score dropped {abs(delta.score_delta):.1f} points "
        f"(from {delta.prior_resilience_score:.1f} to {delta.new_resilience_score:.1f}) "
        f"after importing Month {delta.month} actuals. "
        f"Primary driver: {delta.key_changes[0] if delta.key_changes else 'unknown'}."
    )
    link = f"/blueprints/{delta.blueprint_id}/actuals"

    # Notification center (T37 pattern)
    try:
        from app.services.notification_service import create_notification
        await create_notification(
            db=db,
            workspace_id=workspace_id,
            title="📉 Resilience Score Drift Alert",
            body=message,
            link=link,
            notification_type="drift_alert",
        )
    except Exception as e:
        logger.warning(f"[alert_service] Could not create notification: {e}")

    # Email (T10 pattern)
    try:
        from app.core.email import send_email
        await send_email(
            to=workspace.owner_email,
            subject=f"[Forge] Drift Alert — {workspace.name}",
            body=message + f"\n\nView full report: {link}",
        )
    except Exception as e:
        logger.warning(f"[alert_service] Could not send email: {e}")

    logger.info(f"[alert_service] Alert dispatched for blueprint {delta.blueprint_id}")
```

---

## Step 2 — Create `backend/app/workers/drift_monitor.py`

```python
"""
Celery-beat periodic task: re-simulate each blueprint that has actuals,
compare resilience score, dispatch alert if drop > threshold.
"""
from __future__ import annotations
import asyncio
import logging
from celery import shared_task
from app.db.session import AsyncSessionLocal
from app.services.actuals.variance import compute_variance
from app.services.actuals.alert_service import should_alert, dispatch_drift_alert

logger = logging.getLogger(__name__)


@shared_task(name="workers.drift_monitor.check_all_blueprints")
def check_all_blueprints():
    """Check all blueprints with actuals for resilience drift."""
    asyncio.get_event_loop().run_until_complete(_check_all())


async def _check_all():
    from sqlalchemy import select, distinct
    from app.models.actuals import ActualsRecord

    async with AsyncSessionLocal() as db:
        # Get all unique (blueprint_id, workspace_id) pairs that have actuals
        result = await db.execute(
            select(ActualsRecord.blueprint_id, ActualsRecord.workspace_id).distinct()
        )
        pairs = result.all()

    logger.info(f"[drift_monitor] Checking {len(pairs)} blueprints with actuals")

    for blueprint_id, workspace_id in pairs:
        try:
            async with AsyncSessionLocal() as db:
                delta = await compute_variance(blueprint_id, workspace_id, db, mc_runs=30)
                if await should_alert(delta):
                    await dispatch_drift_alert(delta, workspace_id, db)
                    logger.info(f"[drift_monitor] Alert triggered for {blueprint_id}: score_delta={delta.score_delta:.1f}")
                else:
                    logger.debug(f"[drift_monitor] No alert for {blueprint_id}: score_delta={delta.score_delta:.1f}")
        except Exception as e:
            logger.error(f"[drift_monitor] Error checking {blueprint_id}: {e}")
```

---

## Step 3 — Register Celery-beat schedule

In `backend/app/core/celery_app.py` (or wherever beat_schedule is defined):

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    **app.conf.beat_schedule,
    "drift-monitor-daily": {
        "task": "workers.drift_monitor.check_all_blueprints",
        "schedule": crontab(hour=7, minute=0),   # Run daily at 7am UTC
    },
}
```

---

## Step 4 — Tests

`backend/tests/unit/actuals/test_drift_monitor.py`:

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.actuals.alert_service import should_alert
from app.services.actuals.variance import VarianceDelta


def _make_delta(score_delta: float) -> VarianceDelta:
    return VarianceDelta(
        blueprint_id="bp_001", month=3,
        prior_survival_rate=0.72, new_survival_rate=0.58,
        survival_delta=-0.14,
        prior_runway_median=19.0, new_runway_median=14.0, runway_delta=-5.0,
        prior_resilience_score=68.0, new_resilience_score=68.0 + score_delta,
        score_delta=score_delta, key_changes=["churn increased"]
    )


def test_should_alert_above_threshold():
    delta = _make_delta(-6.0)   # 6pp drop
    assert asyncio.get_event_loop().run_until_complete(should_alert(delta)) is True


def test_should_not_alert_below_threshold():
    delta = _make_delta(-3.0)   # 3pp drop (below 5pp threshold)
    assert asyncio.get_event_loop().run_until_complete(should_alert(delta)) is False


def test_should_not_alert_positive_delta():
    delta = _make_delta(2.0)    # improvement
    assert asyncio.get_event_loop().run_until_complete(should_alert(delta)) is False


def test_dispatch_alert_calls_notification(monkeypatch):
    from app.services.actuals import alert_service
    notif_calls = []
    async def mock_create(db, workspace_id, title, body, link, notification_type):
        notif_calls.append({"title": title, "body": body})
    monkeypatch.setattr("app.services.actuals.alert_service.create_notification", mock_create)

    async def mock_get_workspace(ws_id, db):
        ws = MagicMock(); ws.owner_email = "test@example.com"; ws.name = "TestCo"
        return ws
    monkeypatch.setattr("app.services.actuals.alert_service.get_workspace", mock_get_workspace)
    monkeypatch.setattr("app.services.actuals.alert_service.send_email", AsyncMock())

    delta = _make_delta(-7.0)
    asyncio.get_event_loop().run_until_complete(
        alert_service.dispatch_drift_alert(delta, "ws_001", AsyncMock())
    )
    assert len(notif_calls) == 1
    assert "Drift Alert" in notif_calls[0]["title"]
```

---

## Verification Commands

```bash
cd backend && pytest tests/unit/actuals/test_drift_monitor.py -v
cd backend && ruff check app/workers/drift_monitor.py app/services/actuals/alert_service.py
# Manually trigger task:
cd backend && celery -A app.core.celery_app call workers.drift_monitor.check_all_blueprints
```
