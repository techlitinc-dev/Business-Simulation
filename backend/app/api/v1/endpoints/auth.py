"""Auth endpoints: register, login, refresh, verify-email."""

import logging

from fastapi import APIRouter

from app.api.deps import DbSession
from app.core.security import create_access_token, create_refresh_token
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    VerifyEmailRequest,
)
from app.schemas.user import UserOut
from app.services import auth_service

logger = logging.getLogger("forge.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


def _enqueue_verification_email(user_id: str) -> None:
    """Enqueue the verification email task, falling back to a log if the
    worker/broker is unavailable (T10 wires the real task)."""
    try:
        from app.workers.email_tasks import send_verification_email_task

        send_verification_email_task.delay(user_id)
    except Exception:  # noqa: BLE001 — broker down in dev is non-fatal
        logger.warning("verification email not enqueued (broker unavailable)", exc_info=True)


@router.post("/register", status_code=201)
async def register(payload: RegisterRequest, db: DbSession) -> UserOut:
    user = await auth_service.register_user(
        db, email=payload.email, name=payload.name, password=payload.password
    )
    _enqueue_verification_email(str(user.id))
    return UserOut.model_validate(user)


@router.post("/login")
async def login(payload: LoginRequest, db: DbSession) -> TokenPair:
    user = await auth_service.authenticate_user(
        db, email=payload.email, password=payload.password
    )
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh")
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    return auth_service.refresh_tokens(db, payload.refresh_token)


@router.post("/verify-email")
async def verify_email(payload: VerifyEmailRequest, db: DbSession) -> dict[str, str]:
    await auth_service.verify_email(db, payload.token)
    return {"detail": "email verified"}
