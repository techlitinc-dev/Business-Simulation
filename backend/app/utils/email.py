"""Email layer: backend protocol, SMTP + console implementations, helpers."""

from email.message import EmailMessage
from typing import Protocol

import aiosmtplib
import structlog

from app.core.config import get_settings

logger = structlog.get_logger("forge.email")


class EmailBackend(Protocol):
    async def send(
        self, to: str, subject: str, body_text: str, body_html: str | None = None
    ) -> None: ...


class SMTPEmailBackend:
    def __init__(self) -> None:
        settings = get_settings()
        self.host = settings.smtp_host or ""
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.tls = settings.smtp_tls
        self.sender = settings.emails_from

    async def send(
        self, to: str, subject: str, body_text: str, body_html: str | None = None
    ) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body_text)
        if body_html:
            message.add_alternative(body_html, subtype="html")

        client = aiosmtplib.SMTP(
            hostname=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            start_tls=self.tls,
        )
        async with client:
            await client.send_message(message)


class ConsoleEmailBackend:
    """Logs the full email via structlog — the dev/test default."""

    async def send(
        self, to: str, subject: str, body_text: str, body_html: str | None = None
    ) -> None:
        logger.info(
            "email (console backend)",
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )


def get_email_backend() -> EmailBackend:
    settings = get_settings()
    if settings.smtp_host:
        return SMTPEmailBackend()
    return ConsoleEmailBackend()


def _verification_url(token: str) -> str:
    settings = get_settings()
    return f"{settings.frontend_url}/verify-email?token={token}"


async def send_verification_email(to: str, token: str) -> None:
    url = _verification_url(token)
    body_text = (
        f"Welcome to The Forge!\n\n"
        f"Verify your email to activate your account:\n{url}\n\n"
        f"If you did not sign up, you can ignore this email."
    )
    body_html = (
        f"<p>Welcome to The Forge!</p>"
        f"<p>Verify your email to activate your account:</p>"
        f'<p><a href="{url}">{url}</a></p>'
    )
    await get_email_backend().send(
        to, "Verify your email — The Forge", body_text, body_html
    )


async def send_invite_email(
    to: str, workspace_name: str, inviter_name: str, invite_url: str
) -> None:
    body_text = (
        f"{inviter_name} invited you to join the workspace '{workspace_name}' "
        f"on The Forge.\n\nAccept the invite here:\n{invite_url}\n"
    )
    body_html = (
        f"<p>{inviter_name} invited you to join the workspace "
        f"<strong>{workspace_name}</strong> on The Forge.</p>"
        f'<p><a href="{invite_url}">Accept the invite</a></p>'
    )
    await get_email_backend().send(
        to, f"You're invited to {workspace_name} — The Forge", body_text, body_html
    )
