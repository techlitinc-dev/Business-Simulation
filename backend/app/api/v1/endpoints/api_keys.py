"""API key endpoints (T45) — JWT-authenticated, workspace admin/owner only."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession
from app.core.exceptions import DomainError
from app.models.workspace import Membership, Role
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse
from app.services import api_key_service

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

# Role rank: owner=3 > admin=2 > member=1
_ROLE_RANK = {Role.OWNER: 3, Role.ADMIN: 2, Role.MEMBER: 1}


async def _require_admin_membership(
    db: DbSession,
    workspace: CurrentWorkspace,
    user: CurrentUser,
) -> Membership:
    """Resolve the caller's membership and require owner/admin (403 otherwise)."""
    membership = await db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.workspace_id == workspace.id,
        )
    )
    if membership is None or _ROLE_RANK[membership.role] < _ROLE_RANK[Role.ADMIN]:
        raise DomainError(status_code=403, detail="Requires admin or owner role")
    return membership


@router.post("", status_code=status.HTTP_201_CREATED, response_model=None)
async def create_key(
    payload: ApiKeyCreate,
    db: DbSession,
    workspace: CurrentWorkspace,
    user: CurrentUser,
) -> ApiKeyCreatedResponse:
    """Create an API key — plaintext returned exactly once."""
    await _require_admin_membership(db, workspace, user)
    response, _ = await api_key_service.create_api_key(
        db,
        workspace_id=workspace.id,
        name=payload.name,
        scopes=payload.scopes,
        rate_limit_rpm=payload.rate_limit_rpm,
    )
    return response


@router.get("", response_model=list[ApiKeyResponse])
async def list_keys(
    db: DbSession,
    workspace: CurrentWorkspace,
    user: CurrentUser,
) -> list[ApiKeyResponse]:
    await _require_admin_membership(db, workspace, user)
    return await api_key_service.list_api_keys(db, workspace_id=workspace.id)


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def revoke_key(
    api_key_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
    user: CurrentUser,
) -> None:
    await _require_admin_membership(db, workspace, user)
    try:
        await api_key_service.revoke_api_key(
            db, workspace_id=workspace.id, api_key_id=api_key_id
        )
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return None
