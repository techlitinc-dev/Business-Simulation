"""Workspace, membership, and invite schemas."""

import re
import secrets
import uuid
from datetime import datetime
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, EmailStr, Field


def slugify(name: str) -> str:
    """Slugify a name and append a 4-char random suffix for uniqueness."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        slug = "workspace"
    return f"{slug}-{secrets.token_hex(2)}"


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan_tier: str
    role: str


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: str
    name: str
    role: str
    joined_at: datetime


class MemberRoleUpdate(BaseModel):
    role: Literal["owner", "admin", "member"]


class InviteCreate(BaseModel):
    email: EmailStr
    role: Literal["admin", "member"] = "member"


class InviteOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    invite_url: str
    expires_at: datetime


class InviteAcceptOut(BaseModel):
    workspace_id: uuid.UUID
    role: str


def build_invite_url(base_url: str, token: str) -> str:
    return f"{base_url}/accept-invite?token={quote(token)}"
