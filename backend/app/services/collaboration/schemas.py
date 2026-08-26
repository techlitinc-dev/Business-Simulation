"""Comment and approval request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TargetType = Literal["blueprint", "run", "report", "section"]


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_type: TargetType
    target_id: str = Field(min_length=1)
    body: str = Field(min_length=1)
    mentions: list[str] = Field(default_factory=list)
    section_ref: str | None = None


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    body: str
    author_user_id: str
    created_at: datetime

    @field_validator("author_user_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, value: object) -> object:
        return str(value) if isinstance(value, uuid.UUID) else value


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_type: TargetType
    target_id: str = Field(min_length=1)


class ApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approved", "rejected"]
    note: str = ""


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    decided_at: datetime | None
