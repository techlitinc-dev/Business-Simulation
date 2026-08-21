"""Outbound webhook registration endpoints (admin/owner, workspace-scoped)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession
from app.core.exceptions import DomainError
from app.models.workspace import Membership, Role
from app.schemas.webhook import WebhookCreate, WebhookCreatedResponse, WebhookOut
from app.services import webhook_service

router = APIRouter(prefix="/integrations/webhooks", tags=["integrations"])

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


@router.post("", status_code=status.HTTP_201_CREATED, response_model=WebhookCreatedResponse)
async def create_webhook(
    payload: WebhookCreate,
    db: DbSession,
    workspace: CurrentWorkspace,
    user: CurrentUser,
) -> WebhookCreatedResponse:
    """Register a webhook — plaintext secret returned exactly once."""
    await _require_admin_membership(db, workspace, user)
    return await webhook_service.create_webhook(
        db, workspace_id=workspace.id, data=payload
    )


@router.get("", response_model=list[WebhookOut])
async def list_webhooks(
    db: DbSession,
    workspace: CurrentWorkspace,
    user: CurrentUser,
) -> list[WebhookOut]:
    await _require_admin_membership(db, workspace, user)
    registrations = await webhook_service.list_webhooks(
        db, workspace_id=workspace.id
    )
    return [WebhookOut.model_validate(r) for r in registrations]


@router.delete(
    "/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_webhook(
    webhook_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
    user: CurrentUser,
) -> None:
    await _require_admin_membership(db, workspace, user)
    try:
        await webhook_service.delete_webhook(
            db, workspace_id=workspace.id, webhook_id=webhook_id
        )
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return None
