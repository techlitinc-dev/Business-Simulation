"""Workspace endpoints: CRUD, members, invites, accept."""

import logging
import uuid

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import (
    CurrentUser,
    DbSession,
    require_member_removal,
    require_workspace_role,
)
from app.models.workspace import Membership, Role
from app.schemas.workspace import (
    InviteAcceptOut,
    InviteCreate,
    InviteOut,
    MemberOut,
    MemberRoleUpdate,
    WorkspaceCreate,
    WorkspaceOut,
    WorkspaceUpdate,
)
from app.services import workspace_service

logger = logging.getLogger("forge.workspaces")

router = APIRouter(tags=["workspaces"])

guard_member = Depends(require_workspace_role("member"))
guard_admin = Depends(require_workspace_role("admin"))
guard_owner = Depends(require_workspace_role("owner"))
guard_member_removal = Depends(require_member_removal())


def _enqueue_invite_email(invite_id: str) -> None:
    """Enqueue the invite email task, falling back to a log if the
    worker/broker is unavailable (T10 wires the real task)."""
    try:
        from app.workers.email_tasks import send_invite_email_task

        send_invite_email_task.delay(invite_id)
    except Exception:  # noqa: BLE001 — broker down in dev is non-fatal
        logger.warning("invite email not enqueued (broker unavailable)", exc_info=True)


@router.post("/workspaces", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate, db: DbSession, user: CurrentUser
) -> WorkspaceOut:
    return await workspace_service.create_workspace(db, name=payload.name, owner=user)


@router.get("/workspaces")
async def list_workspaces(db: DbSession, user: CurrentUser) -> list[WorkspaceOut]:
    return await workspace_service.list_workspaces(db, user=user)


@router.get("/workspaces/{workspace_id}")
async def get_workspace(
    workspace_id: uuid.UUID,
    db: DbSession,
    membership: Membership = guard_member,
) -> WorkspaceOut:
    workspace = await workspace_service.get_workspace(db, workspace_id=workspace_id)
    return workspace_service.to_workspace_out(workspace, membership)


@router.patch("/workspaces/{workspace_id}")
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    db: DbSession,
    membership: Membership = guard_admin,
) -> WorkspaceOut:
    workspace = await workspace_service.get_workspace(db, workspace_id=workspace_id)
    return await workspace_service.update_workspace(
        db, workspace=workspace, membership=membership, name=payload.name
    )


@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: uuid.UUID,
    db: DbSession,
    membership: Membership = guard_owner,
) -> Response:
    workspace = await workspace_service.get_workspace(db, workspace_id=workspace_id)
    await workspace_service.delete_workspace(db, workspace=workspace)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/workspaces/{workspace_id}/members")
async def list_members(
    workspace_id: uuid.UUID,
    db: DbSession,
    membership: Membership = guard_member,
) -> list[MemberOut]:
    return await workspace_service.list_members(db, workspace_id=workspace_id)


@router.patch("/workspaces/{workspace_id}/members/{user_id}")
async def update_member_role(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: MemberRoleUpdate,
    db: DbSession,
    actor: Membership = guard_admin,
) -> MemberOut:
    workspace = await workspace_service.get_workspace(db, workspace_id=workspace_id)
    target = await workspace_service.get_member(
        db, workspace_id=workspace_id, user_id=user_id
    )
    return await workspace_service.update_member_role(
        db, workspace=workspace, actor=actor, target=target, new_role=Role(payload.role)
    )


@router.delete(
    "/workspaces/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    db: DbSession,
    actor: Membership = guard_member_removal,
) -> Response:
    workspace = await workspace_service.get_workspace(db, workspace_id=workspace_id)
    target = await workspace_service.get_member(
        db, workspace_id=workspace_id, user_id=user_id
    )
    await workspace_service.remove_member(
        db, workspace=workspace, actor=actor, target=target
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/workspaces/{workspace_id}/invites", status_code=status.HTTP_201_CREATED)
async def create_invite(
    workspace_id: uuid.UUID,
    payload: InviteCreate,
    db: DbSession,
    membership: Membership = guard_admin,
) -> InviteOut:
    workspace = await workspace_service.get_workspace(db, workspace_id=workspace_id)
    invite = await workspace_service.create_invite(
        db, workspace=workspace, email=payload.email, role=Role(payload.role)
    )
    _enqueue_invite_email(str(invite.id))
    invite_url = await workspace_service.invite_to_url(invite)
    return InviteOut(
        id=invite.id,
        email=invite.email,
        role=invite.role,
        invite_url=invite_url,
        expires_at=invite.expires_at,
    )


@router.post("/invites/{token}/accept")
async def accept_invite(
    token: str, db: DbSession, user: CurrentUser
) -> InviteAcceptOut:
    workspace, role = await workspace_service.accept_invite(db, token=token, user=user)
    return InviteAcceptOut(workspace_id=workspace.id, role=role)
