"""T48 unit tests: Sentry init gating + request-id binding."""

import pytest


def test_sentry_not_initialized_without_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    """With an empty SENTRY_DSN the app boots without calling sentry_sdk.init."""
    from app.core.config import get_settings

    settings = get_settings()
    settings.sentry_dsn = ""

    calls: list[dict] = []

    def _fake_init(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("sentry_sdk.init", _fake_init)

    from app.main import create_app

    create_app()
    assert calls == []


def test_sentry_initialized_when_dsn_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """With a SENTRY_DSN set, sentry_sdk.init is called with the DSN."""
    from app.core.config import get_settings

    settings = get_settings()
    settings.sentry_dsn = "https://fake@sentry.example/1"
    settings.sentry_traces_sample_rate = 0.5

    calls: list[dict] = []

    def _fake_init(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("sentry_sdk.init", _fake_init)

    from app.main import create_app

    create_app()
    assert len(calls) == 1
    assert calls[0]["dsn"] == "https://fake@sentry.example/1"
    assert calls[0]["traces_sample_rate"] == 0.5
    # Reset so later tests don't see a DSN.
    settings.sentry_dsn = ""
    settings.sentry_traces_sample_rate = 0.0


def test_bind_request_id_uses_client_value() -> None:
    from app.core.logging import bind_request_id

    class _FakeRequest:
        headers = {"X-Request-ID": "client-id-abc"}

    request_id = bind_request_id(_FakeRequest())  # type: ignore[arg-type]
    assert request_id == "client-id-abc"


def test_bind_request_id_generates_when_missing() -> None:
    from app.core.logging import bind_request_id

    class _FakeRequest:
        headers = {}

    request_id = bind_request_id(_FakeRequest())  # type: ignore[arg-type]
    assert request_id and len(request_id) == 32  # uuid4().hex
