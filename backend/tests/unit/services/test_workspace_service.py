"""Unit tests for workspace service logic: slug, roles, invites."""

from datetime import UTC, datetime, timedelta

import pytest
from app.core.exceptions import DomainError
from app.db.base import Base
from app.models.workspace import Invite, Role, Workspace
from app.schemas.workspace import slugify
from app.services import workspace_service
from app.services.auth_service import register_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture
async def db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def test_slugify() -> None:
    assert slugify("My Great Company").startswith("my-great-company-")
    s = slugify("   ")
    assert s.startswith("workspace-") and len(s.split("-")[-1]) == 4
    s1, s2 = slugify("Same"), slugify("Same")
    assert s1 != s2  # random suffix


async def test_role_rank() -> None:
    assert workspace_service.role_rank(Role.OWNER) > workspace_service.role_rank(
        Role.ADMIN
    ) > workspace_service.role_rank(Role.MEMBER)


async def test_register_creates_personal_workspace(db: AsyncSession) -> None:
    user = await register_user(db, email="p@b.co", name="Personal", password="password123")
    workspaces = await workspace_service.list_workspaces(db, user=user)
    assert len(workspaces) == 1
    assert workspaces[0].name == "Personal's Workspace"
    assert workspaces[0].role == "owner"


async def test_create_workspace_and_membership(db: AsyncSession) -> None:
    user = await register_user(db, email="c@b.co", name="C", password="password123")
    out = await workspace_service.create_workspace(db, name="Second", owner=user)
    assert out.name == "Second"
    assert out.role == "owner"


async def test_invite_expiry_checked(db: AsyncSession) -> None:
    await register_user(db, email="i@b.co", name="I", password="password123")
    ws = await db.scalar(select(Workspace))
    invite = Invite(
        token="expiredtoken",
        email="ghost@b.co",
        role=Role.MEMBER,
        workspace_id=ws.id,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    db.add(invite)
    await db.commit()

    ghost = await register_user(db, email="ghost2@b.co", name="G", password="password123")
    with pytest.raises(DomainError) as exc:
        await workspace_service.accept_invite(db, token="expiredtoken", user=ghost)
    assert exc.value.status_code == 410


async def test_accept_invite_creates_membership(db: AsyncSession) -> None:
    await register_user(db, email="o@b.co", name="O", password="password123")
    ws = await db.scalar(select(Workspace))
    invite = Invite(
        token="goodtoken",
        email="newbie@b.co",
        role=Role.ADMIN,
        workspace_id=ws.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    db.add(invite)
    await db.commit()

    newbie = await register_user(db, email="newbie@b.co", name="N", password="password123")
    ws_out, role = await workspace_service.accept_invite(
        db, token="goodtoken", user=newbie
    )
    assert role == Role.ADMIN
    assert ws_out.id == ws.id

    # owner still there; newbie now admin
    members = await workspace_service.list_members(db, workspace_id=ws.id)
    by_email = {m.email: m.role for m in members}
    assert by_email == {"o@b.co": "owner", "newbie@b.co": "admin"}


async def test_accept_invite_twice_raises_409(db: AsyncSession) -> None:
    await register_user(db, email="oo@b.co", name="Oo", password="password123")
    ws = await db.scalar(select(Workspace))
    invite = Invite(
        token="twice",
        email="twice@b.co",
        role=Role.MEMBER,
        workspace_id=ws.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    db.add(invite)
    await db.commit()

    newbie = await register_user(db, email="twice@b.co", name="T", password="password123")
    await workspace_service.accept_invite(db, token="twice", user=newbie)
    with pytest.raises(DomainError) as exc:
        await workspace_service.accept_invite(db, token="twice", user=newbie)
    assert exc.value.status_code == 409


async def test_member_role_guard_only_owner_can_promote(db: AsyncSession) -> None:
    owner = await register_user(db, email="ow@b.co", name="Ow", password="password123")
    ws = await db.scalar(select(Workspace))
    invite = Invite(
        token="promo",
        email="m@b.co",
        role=Role.MEMBER,
        workspace_id=ws.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    db.add(invite)
    await db.commit()

    member = await register_user(db, email="m@b.co", name="M", password="password123")
    await workspace_service.accept_invite(db, token="promo", user=member)

    member_membership = await workspace_service.get_member(
        db, workspace_id=ws.id, user_id=member.id
    )
    target = await workspace_service.get_member(
        db, workspace_id=ws.id, user_id=member.id
    )

    # member cannot promote to admin
    with pytest.raises(DomainError) as exc:
        await workspace_service.update_member_role(
            db,
            workspace=ws,
            actor=member_membership,
            target=target,
            new_role=Role.ADMIN,
        )
    assert exc.value.status_code == 403

    # owner can promote
    owner_membership = await workspace_service.get_member(
        db, workspace_id=ws.id, user_id=owner.id
    )
    result = await workspace_service.update_member_role(
        db,
        workspace=ws,
        actor=owner_membership,
        target=target,
        new_role=Role.ADMIN,
    )
    assert result.role == "admin"


async def test_last_owner_removal_guard(db: AsyncSession) -> None:
    owner = await register_user(db, email="last@b.co", name="Last", password="password123")
    ws = await db.scalar(select(Workspace))
    owner_membership = await workspace_service.get_member(
        db, workspace_id=ws.id, user_id=owner.id
    )
    with pytest.raises(DomainError) as exc:
        await workspace_service.remove_member(
            db, workspace=ws, actor=owner_membership, target=owner_membership
        )
    assert exc.value.status_code == 409
