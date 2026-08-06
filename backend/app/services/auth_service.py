"""Auth business logic: registration, authentication, token refresh."""

import logging
import uuid

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.models.workspace import Membership, Role, Workspace
from app.schemas.auth import TokenPair
from app.schemas.workspace import slugify
from app.workers.email_tasks import load_verification_token

logger = logging.getLogger("forge.auth_service")


async def register_user(
    db: AsyncSession, *, email: str, name: str, password: str
) -> User:
    normalized_email = email.strip().lower()

    existing = await db.scalar(
        select(User).where(User.email == normalized_email)
    )
    if existing is not None:
        raise DomainError(status_code=409, detail="Email already registered")

    user = User(
        email=normalized_email,
        name=name.strip(),
        pw_hash=hash_password(password),
        is_verified=False,
    )
    db.add(user)
    await db.flush()

    # Auto-create a personal workspace owned by the new user.
    workspace = Workspace(
        name=f"{name.strip()}'s Workspace",
        slug=slugify(f"{name}-workspace"),
    )
    db.add(workspace)
    await db.flush()
    db.add(
        Membership(
            user_id=user.id,
            workspace_id=workspace.id,
            role=Role.OWNER,
        )
    )

    await db.commit()
    # Refresh inside a fresh transaction (post-commit instances are expired).
    async with db.begin():
        await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, *, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    user = await db.scalar(select(User).where(User.email == normalized_email))
    # Identical message for unknown email / wrong password (no user enumeration).
    if user is None or not verify_password(password, user.pw_hash):
        raise DomainError(status_code=401, detail="Invalid email or password")
    return user


def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError as exc:
        raise DomainError(status_code=401, detail="Invalid or expired refresh token") from exc

    if payload.get("type") != "refresh":
        raise DomainError(status_code=401, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise DomainError(status_code=401, detail="Invalid or expired refresh token")

    # Token rotation: issue a fresh pair.
    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


async def change_password(
    db: AsyncSession,
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """Verify the current password and store a new hash (T38).

    Raises 401/DomainError 400 on a mismatch — spec: 400 with
    "Current password is incorrect".
    """
    if not verify_password(current_password, user.pw_hash):
        raise DomainError(status_code=400, detail="Current password is incorrect")

    user.pw_hash = hash_password(new_password)
    await db.commit()


async def verify_email(db: AsyncSession, token: str) -> None:
    """Verify a user's email from a signed, time-limited token."""
    user_id = load_verification_token(token)
    if user_id is None:
        raise DomainError(status_code=400, detail="Invalid or expired verification token")

    try:
        user = await db.get(User, uuid.UUID(user_id))
    except ValueError as exc:
        raise DomainError(
            status_code=400, detail="Invalid or expired verification token"
        ) from exc

    if user is None:
        raise DomainError(status_code=400, detail="Invalid or expired verification token")

    user.is_verified = True
    await db.commit()
