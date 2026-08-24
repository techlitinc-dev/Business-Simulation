"""Workspace business logic: CRUD, memberships, invites, RBAC."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.models.user import User
from app.models.workspace import Invite, Membership, Role, Workspace
from app.schemas.workspace import MemberOut, WorkspaceOut, build_invite_url, slugify

INVITE_TTL_DAYS = 7


def role_rank(role: Role) -> int:
    return {Role.OWNER: 3, Role.ADMIN: 2, Role.MEMBER: 1}[role]


def _workspace_out(workspace: Workspace, membership: Membership) -> WorkspaceOut:
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        plan_tier=workspace.plan_tier,
        role=membership.role,
        benchmark_opt_in=workspace.benchmark_opt_in,
    )


# Public alias for endpoint use.
to_workspace_out = _workspace_out


async def create_workspace(
    db: AsyncSession, *, name: str, owner: User
) -> WorkspaceOut:
    workspace = Workspace(name=name.strip(), slug=slugify(name))
    db.add(workspace)
    await db.flush()

    membership = Membership(
        user_id=owner.id, workspace_id=workspace.id, role=Role.OWNER
    )
    db.add(membership)
    await db.commit()
    await db.refresh(workspace)
    return _workspace_out(workspace, membership)


async def list_workspaces(db: AsyncSession, *, user: User) -> list[WorkspaceOut]:
    rows = await db.execute(
        select(Workspace, Membership)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == user.id)
        .order_by(Workspace.created_at)
    )
    return [_workspace_out(ws, mem) for ws, mem in rows.all()]


async def get_workspace(db: AsyncSession, *, workspace_id: uuid.UUID) -> Workspace:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise DomainError(status_code=403, detail="Not a member of this workspace")
    return workspace


async def update_workspace(
    db: AsyncSession,
    *,
    workspace: Workspace,
    membership: Membership,
    name: str,
    benchmark_opt_in: bool | None = None,
) -> WorkspaceOut:
    workspace.name = name.strip()
    if benchmark_opt_in is not None:
        workspace.benchmark_opt_in = benchmark_opt_in
    await db.commit()
    await db.refresh(workspace)
    return _workspace_out(workspace, membership)


async def delete_workspace(db: AsyncSession, *, workspace: Workspace) -> None:
    await db.delete(workspace)
    await db.commit()


async def list_members(db: AsyncSession, *, workspace_id: uuid.UUID) -> list[MemberOut]:
    rows = await db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.workspace_id == workspace_id)
        .order_by(Membership.created_at)
    )
    members = []
    for mem, user in rows.all():
        members.append(
            MemberOut(
                user_id=user.id,
                email=user.email,
                name=user.name,
                role=mem.role,
                joined_at=mem.created_at,
            )
        )
    return members


async def get_member(
    db: AsyncSession, *, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> Membership:
    member = await db.scalar(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == user_id,
        )
    )
    if member is None:
        raise DomainError(status_code=404, detail="Member not found")
    return member


async def add_member(
    db: AsyncSession, *, workspace_id: uuid.UUID, user_id: uuid.UUID, role: Role = Role.MEMBER
) -> Membership:
    """Add a user to a workspace, or return the existing membership (SCIM)."""
    existing = await db.scalar(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == user_id,
        )
    )
    if existing is not None:
        return existing
    membership = Membership(
        user_id=user_id, workspace_id=workspace_id, role=role
    )
    db.add(membership)
    await db.flush()
    return membership


async def update_member_role(
    db: AsyncSession,
    *,
    workspace: Workspace,
    actor: Membership,
    target: Membership,
    new_role: Role,
) -> MemberOut:
    """Change a member's role. Only the owner may grant/revoke owner/admin."""
    if new_role in (Role.OWNER, Role.ADMIN) and actor.role != Role.OWNER:
        raise DomainError(status_code=403, detail="Only the owner can manage owner/admin roles")

    # The owner role can only be held by one person: revoke it from the actor
    # when handing ownership over.
    if target.role == Role.OWNER or new_role == Role.OWNER:
        if actor.role != Role.OWNER:
            raise DomainError(status_code=403, detail="Only the owner can manage the owner role")
        if new_role == Role.OWNER:
            actor.role = Role.MEMBER
            await db.flush()

    target.role = new_role
    await db.commit()

    user = await db.get(User, target.user_id)
    if user is None:  # pragma: no cover — FK guarantees existence
        raise DomainError(status_code=404, detail="Member not found")
    return MemberOut(
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=target.role,
        joined_at=target.created_at,
    )


async def remove_member(
    db: AsyncSession,
    *,
    workspace: Workspace,
    actor: Membership,
    target: Membership,
) -> None:
    """Remove a member. Guards: last owner cannot be removed; an admin may
    remove members; self-removal is allowed."""
    if actor.role == Role.MEMBER and actor.user_id != target.user_id:
        raise DomainError(status_code=403, detail="Only admins can remove members")

    if target.role == Role.OWNER:
        owners = (
            await db.execute(
                select(Membership).where(
                    Membership.workspace_id == workspace.id,
                    Membership.role == Role.OWNER,
                )
            )
        ).scalars().all()
        if len(owners) <= 1:
            raise DomainError(status_code=409, detail="Cannot remove the last owner")

    await db.delete(target)
    await db.commit()


async def create_invite(
    db: AsyncSession,
    *,
    workspace: Workspace,
    email: str,
    role: Role,
) -> Invite:
    invite = Invite(
        token=Invite.new_token(),
        email=email.strip().lower(),
        role=role,
        workspace_id=workspace.id,
        expires_at=Invite.default_expiry(),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite


async def accept_invite(
    db: AsyncSession, *, token: str, user: User
) -> tuple[Workspace, Role]:
    invite = await db.scalar(select(Invite).where(Invite.token == token))
    if invite is None:
        raise DomainError(status_code=404, detail="Invite not found")

    now = datetime.now(UTC)
    if invite.expires_at.replace(tzinfo=UTC) < now:
        raise DomainError(status_code=410, detail="Invite has expired")

    existing = await db.scalar(
        select(Membership).where(
            Membership.workspace_id == invite.workspace_id,
            Membership.user_id == user.id,
        )
    )
    if existing is not None:
        raise DomainError(status_code=409, detail="Already a member of this workspace")

    membership = Membership(
        user_id=user.id, workspace_id=invite.workspace_id, role=invite.role
    )
    db.add(membership)
    invite.accepted_at = now
    await db.commit()

    workspace = await db.get(Workspace, invite.workspace_id)
    if workspace is None:  # pragma: no cover — FK guarantees existence
        raise DomainError(status_code=404, detail="Invite not found")
    return workspace, membership.role


async def invite_to_url(invite: Invite) -> str:
    settings = get_settings()
    return build_invite_url(settings.frontend_url, invite.token)
