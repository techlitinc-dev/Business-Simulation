"""Celery tasks for verification and invite emails."""

import asyncio
import threading
import uuid
from collections.abc import Callable
from typing import Any

import structlog
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import get_settings
from app.utils.email import send_invite_email, send_verification_email
from app.workers.celery_app import celery_app

logger = structlog.get_logger("forge.email_tasks")

VERIFY_SALT = "email-verify"
VERIFY_MAX_AGE_SECONDS = 24 * 60 * 60


def create_verification_token(user_id: str) -> str:
    settings = get_settings()
    serializer = URLSafeTimedSerializer(settings.jwt_secret_key, salt=VERIFY_SALT)
    return serializer.dumps(user_id)


def load_verification_token(token: str) -> str | None:
    """Return the user_id if the token is valid and unexpired, else None."""
    settings = get_settings()
    serializer = URLSafeTimedSerializer(settings.jwt_secret_key, salt=VERIFY_SALT)
    try:
        user_id = serializer.loads(token, max_age=VERIFY_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    return str(user_id)


def _task(name: str) -> Callable[[Callable[..., Any]], Any]:
    # Celery's untyped decorator returns Any; cast keeps mypy quiet.
    return celery_app.task(name=name)  # type: ignore[no-any-return]


def _run_coro(coro: Any) -> None:
    """Run a coroutine from a sync Celery task.

    In a real worker there is no running loop, so `asyncio.run` is correct.
    Under pytest's eager mode (`task_always_eager`) the task runs inside the
    test's event loop, where `asyncio.run` raises — execute the coroutine on a
    dedicated thread with its own loop and block until it finishes, so the
    task completes before the caller's DB session is reused (a fire-and-forget
    task would race the shared sqlite StaticPool connection).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
        return

    def _target() -> None:
        asyncio.run(coro)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join()


@_task("forge.send_verification_email")
def send_verification_email_task(user_id: str) -> None:
    from app.db.session import async_session_factory
    from app.models.user import User

    async def _run() -> None:
        async with async_session_factory() as session:
            user = await session.get(User, uuid.UUID(user_id))
            if user is None:
                logger.warning("verification email: user not found", user_id=user_id)
                return
            token = create_verification_token(str(user.id))
            await send_verification_email(user.email, token)

    _run_coro(_run())


@_task("forge.send_invite_email")
def send_invite_email_task(invite_id: str) -> None:
    from app.db.session import async_session_factory
    from app.models.workspace import Invite, Workspace

    async def _run() -> None:
        try:
            invite_id_uuid = uuid.UUID(invite_id)
        except ValueError:
            logger.warning("invite email: invalid invite id", invite_id=invite_id)
            return
        async with async_session_factory() as session:
            invite = await session.get(Invite, invite_id_uuid)
            if invite is None:
                logger.warning("invite email: invite not found", invite_id=invite_id)
                return
            workspace = await session.get(Workspace, invite.workspace_id)
            if workspace is None:
                logger.warning("invite email: workspace not found", invite_id=invite_id)
                return
            settings = get_settings()
            invite_url = f"{settings.frontend_url}/accept-invite?token={invite.token}"
            await send_invite_email(
                invite.email,
                workspace.name,
                inviter_name="A member",
                invite_url=invite_url,
            )

    _run_coro(_run())
