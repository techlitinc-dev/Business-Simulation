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


async def test_dispatch_alert_sends_email_to_owner(monkeypatch: Any) -> None:
    import app.services.actuals.alert_service as alert_service

    sent: list[dict[str, str]] = []

    class FakeBackend:
        async def send(
            self, to: str, subject: str, body_text: str, body_html: str | None = None
        ) -> None:
            sent.append({"to": to, "subject": subject, "body_text": body_text})

    async def mock_owner_email(db: Any, workspace_id: uuid.UUID) -> str:
        return "owner@example.com"

    async def mock_get_workspace(db: Any, *, workspace_id: uuid.UUID) -> MagicMock:
        ws = MagicMock()
        ws.name = "TestCo"
        return ws

    monkeypatch.setattr(alert_service, "_owner_email", mock_owner_email)
    monkeypatch.setattr(alert_service, "get_workspace", mock_get_workspace)
    monkeypatch.setattr(alert_service, "get_email_backend", lambda: FakeBackend())

    delta = _make_delta(-7.0)
    await dispatch_drift_alert(delta, uuid.uuid4(), AsyncMock())

    assert len(sent) == 1
    assert sent[0]["to"] == "owner@example.com"
    assert "Drift Alert" in sent[0]["subject"]
    assert "7.0 points" in sent[0]["body_text"]


async def test_dispatch_alert_no_owner_skips_email(monkeypatch: Any) -> None:
    import app.services.actuals.alert_service as alert_service

    async def mock_owner_email(db: Any, workspace_id: uuid.UUID) -> None:
        return None

    async def mock_get_workspace(db: Any, *, workspace_id: uuid.UUID) -> MagicMock:
        ws = MagicMock()
        ws.name = "TestCo"
        return ws

    monkeypatch.setattr(alert_service, "_owner_email", mock_owner_email)
    monkeypatch.setattr(alert_service, "get_workspace", mock_get_workspace)

    # If send were called with no owner, the backend would be invoked; use a
    # sentinel that fails loudly if touched.
    class ExplodingBackend:
        async def send(self, *args: Any, **kwargs: Any) -> None:
            raise AssertionError("email should not be sent without an owner")

    monkeypatch.setattr(alert_service, "get_email_backend", lambda: ExplodingBackend())

    delta = _make_delta(-6.0)
    await dispatch_drift_alert(delta, uuid.uuid4(), AsyncMock())
