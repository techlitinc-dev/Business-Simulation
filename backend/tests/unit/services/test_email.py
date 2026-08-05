"""Unit tests for the email layer: backend selection, console capture, tokens."""


import pytest
from app.core.config import get_settings
from app.utils.email import ConsoleEmailBackend, SMTPEmailBackend, get_email_backend
from app.workers.email_tasks import (
    VERIFY_SALT,
    create_verification_token,
    load_verification_token,
)
from itsdangerous import URLSafeTimedSerializer


class TestBackendSelection:
    def test_console_backend_when_no_smtp_host(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(get_settings(), "smtp_host", "")
        assert isinstance(get_email_backend(), ConsoleEmailBackend)

    def test_smtp_backend_when_host_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(get_settings(), "smtp_host", "smtp.example.com")
        assert isinstance(get_email_backend(), SMTPEmailBackend)


class TestConsoleBackend:
    async def test_send_logs_full_email(self, capsys: pytest.CaptureFixture[str]) -> None:
        backend = ConsoleEmailBackend()
        await backend.send(
            "to@b.co", "Subject", "body text", "<p>html</p>"
        )
        captured = capsys.readouterr()
        assert "to@b.co" in captured.out
        assert "Subject" in captured.out
        assert "body text" in captured.out


class TestVerificationToken:
    def test_roundtrip(self) -> None:
        token = create_verification_token("user-123")
        assert load_verification_token(token) == "user-123"

    def test_tampered_token_returns_none(self) -> None:
        assert load_verification_token("garbage-token") is None

    def test_expired_token_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        settings = get_settings()
        serializer = URLSafeTimedSerializer(settings.jwt_secret_key, salt=VERIFY_SALT)
        # Sign the token "in 2001"; itsdangerous.timed does `import time`.
        import itsdangerous.timed as _timed

        monkeypatch.setattr(_timed.time, "time", lambda: 1000000000)
        old_token = serializer.dumps("user-123")
        # monkeypatch reverts at test end; verify now (real 2026) -> expired.
        monkeypatch.undo()
        assert load_verification_token(old_token) is None


class TestTaskFallback:
    def test_verify_token_with_no_broker(self) -> None:
        # The token helpers work without any broker/Redis.
        token = create_verification_token("u1")
        assert load_verification_token(token) == "u1"

    def test_signature_error_path(self) -> None:
        # A token signed with the wrong salt is invalid.
        settings = get_settings()
        serializer = URLSafeTimedSerializer(
            settings.jwt_secret_key, salt="wrong-salt"
        )
        token = serializer.dumps("u1")
        assert load_verification_token(token) is None
