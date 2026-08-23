"""Unit tests for the drift monitor alert service (Day 14)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from app.services.actuals.alert_service import dispatch_drift_alert, should_alert
from app.services.actuals.variance import VarianceDelta


def _make_delta(score_delta: float) -> VarianceDelta:
    return VarianceDelta(
        blueprint_id="bp_001",
        month=3,
        prior_survival_rate=0.72,
        new_survival_rate=0.58,
        survival_delta=-0.14,
        prior_runway_median=19.0,
        new_runway_median=14.0,
        runway_delta=-5.0,
        prior_resilience_score=68.0,
        new_resilience_score=68.0 + score_delta,
        score_delta=score_delta,
        key_changes=["churn increased"],
    )


async def test_should_alert_above_threshold() -> None:
    delta = _make_delta(-6.0)  # 6pp drop
    assert await should_alert(delta) is True


async def test_should_not_alert_below_threshold() -> None:
    delta = _make_delta(-3.0)  # 3pp drop (below 5pp threshold)
    assert await should_alert(delta) is False


async def test_should_not_alert_positive_delta() -> None:
    delta = _make_delta(2.0)  # improvement
    assert await should_alert(delta) is False


async def test_dispatch_alert_calls_notification(monkeypatch: Any) -> None:
    """Dispatch fires the T37 notification hook with the alert message."""
    import logging

    import app.services.actuals.alert_service as alert_service

    notifications: list[str] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            if "drift alert notification" in record.getMessage():
                notifications.append(record.getMessage())

    handler = CaptureHandler()
    logger = logging.getLogger("app.services.actuals.alert_service")
    logger.addHandler(handler)
    try:
        async def mock_owner_email(db: Any, workspace_id: uuid.UUID) -> None:
            return None

        async def mock_get_workspace(db: Any, *, workspace_id: uuid.UUID) -> MagicMock:
            ws = MagicMock()
            ws.name = "TestCo"
            return ws

        monkeypatch.setattr(alert_service, "_owner_email", mock_owner_email)
        monkeypatch.setattr(alert_service, "get_workspace", mock_get_workspace)

        delta = _make_delta(-7.0)
        await dispatch_drift_alert(delta, uuid.uuid4(), AsyncMock())
    finally:
        logger.removeHandler(handler)

    assert notifications, "expected the T37 notification hook to fire"
    assert "Drift Alert" in notifications[0]
    assert "7.0 points" in notifications[0]


async def test_celery_task_importable() -> None:
    from app.workers.drift_monitor import check_all_blueprints

    assert callable(check_all_blueprints)
    assert check_all_blueprints.name == "forge.check_all_blueprints"
