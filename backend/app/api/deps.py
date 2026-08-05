"""FastAPI dependency wiring: DB session, current user, workspace RBAC."""

import uuid
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Membership, Role, Workspace

bearer_scheme = HTTPBearer(auto_error=False)

# Role rank: owner=3 > admin=2 > member=1
ROLE_RANK: dict[Role, int] = {
    Role.OWNER: 3,
    Role.ADMIN: 2,
    Role.MEMBER: 1,
}

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        user = await db.get(User, uuid.UUID(user_id))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def _get_membership(db: AsyncSession, user_id: str, workspace_id: str) -> Membership | None:
    result = await db.scalar(
        select(Membership).where(
            Membership.user_id == uuid.UUID(user_id),
            Membership.workspace_id == uuid.UUID(workspace_id),
        )
    )
    return result


async def get_current_workspace(
    db: DbSession,
    user: CurrentUser,
    x_workspace_id: str | None = Header(default=None),
) -> Workspace:
    """Resolve the caller's active workspace from the ``X-Workspace-Id`` header.

    Used by resource routers (blueprints, simulations, ...) that are scoped to
    the workspace the client has selected. Outsiders get 403, mirroring the
    multi-tenant guard used on ``/workspaces/{id}/*`` routes.
    """
    if not x_workspace_id:
        raise DomainError(status_code=403, detail="X-Workspace-Id header is required")

    membership = await _get_membership(db, str(user.id), x_workspace_id)
    if membership is None:
        raise DomainError(status_code=403, detail="Not a member of this workspace")

    workspace = await db.get(Workspace, uuid.UUID(x_workspace_id))
    if workspace is None:
        raise DomainError(status_code=403, detail="Not a member of this workspace")
    return workspace


CurrentWorkspace = Annotated[Workspace, Depends(get_current_workspace)]


def require_workspace_role(min_role: str = "member") -> Callable[..., object]:
    """Factory producing a dependency guarding a workspace endpoint by role.

    Reads `workspace_id` from the path, loads the caller's Membership, and
    raises 403 if absent or if the caller's role rank is below `min_role`.

    Returns the Membership.
    """

    async def _guard(
        db: DbSession,
        user: CurrentUser,
        workspace_id: Annotated[str, Path()],
    ) -> Membership:
        membership = await _get_membership(db, str(user.id), workspace_id)
        if membership is None:
            # Consistent with the no-cross-tenant-leak choice: an outsider gets
            # 403 (not 404) on every /workspaces/{id}/* route.
            raise DomainError(status_code=403, detail="Not a member of this workspace")

        required = ROLE_RANK.get(Role(min_role), ROLE_RANK[Role.MEMBER])
        if ROLE_RANK[membership.role] < required:
            raise DomainError(
                status_code=403,
                detail=f"Requires role '{min_role}' or higher",
            )
        return membership

    return _guard


def require_member_removal() -> Callable[..., object]:
    """Dependency for member removal: admin+ or the member removing themselves.

    Returns the caller's Membership.
    """

    async def _guard(
        db: DbSession,
        user: CurrentUser,
        workspace_id: Annotated[str, Path()],
        user_id: Annotated[str, Path()],
    ) -> Membership:
        membership = await _get_membership(db, str(user.id), workspace_id)
        if membership is None:
            raise DomainError(status_code=403, detail="Not a member of this workspace")

        is_self = str(user.id) == user_id
        if not is_self and ROLE_RANK[membership.role] < ROLE_RANK[Role.ADMIN]:
            raise DomainError(status_code=403, detail="Only admins can remove members")
        return membership

    return _guard
