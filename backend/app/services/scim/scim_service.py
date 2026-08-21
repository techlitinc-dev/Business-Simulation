"""SCIM provisioning business logic: create users, add to workspaces, deactivate."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError
from app.models.user import User
from app.services.auth_service import (
    create_sso_user,
    deactivate_user,
    get_user_by_email,
)
from app.services.scim.schemas import ScimUser, ScimUserResponse
from app.services.workspace_service import add_member

logger = logging.getLogger("forge.scim")


async def provision_user(
    scim_user: ScimUser, workspace_id: str, db: AsyncSession
) -> ScimUserResponse:
    """Create a user via SCIM and add them to the workspace (idempotent)."""
    from app.models.workspace import Role

    try:
        ws_id = uuid.UUID(workspace_id)
    except ValueError as exc:
        raise DomainError(status_code=400, detail="Invalid workspace_id") from exc

    user = await get_user_by_email(db, scim_user.userName)
    if user is None:
        user = await create_sso_user(
            db, email=scim_user.userName, name=scim_user.displayName
        )
        logger.info("[scim] Provisioned user: %s", scim_user.userName)

    await add_member(workspace_id=ws_id, user_id=user.id, role=Role.MEMBER, db=db)
    await db.commit()
    return ScimUserResponse(
        id=user.id,
        userName=user.email,
        displayName=user.name,
        active=user.is_active,
    )


async def deprovision_user(user_id: str, db: AsyncSession) -> bool:
    """Deactivate (not delete) a user account."""
    deactivated = await deactivate_user(db, user_id)
    if deactivated:
        logger.info("[scim] Deprovisioned user: %s", user_id)
    return deactivated


async def get_scim_user(user_id: str, db: AsyncSession) -> ScimUserResponse:
    """Load a SCIM user resource by id, or raise 404."""
    try:
        user = await db.get(User, uuid.UUID(user_id))
    except ValueError as exc:
        raise DomainError(status_code=404, detail="User not found") from exc
    if user is None:
        raise DomainError(status_code=404, detail="User not found")
    return ScimUserResponse(
        id=user.id,
        userName=user.email,
        displayName=user.name,
        active=user.is_active,
    )
