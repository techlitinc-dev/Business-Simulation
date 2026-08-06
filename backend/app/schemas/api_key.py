"""API key request/response schemas (T45)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    scopes: list[Literal["runs:read", "runs:write", "reports:read", "blueprints:read"]]
    rate_limit_rpm: int = Field(default=60, ge=1, le=10000)


class ApiKeyCreatedResponse(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: list[str]
    key: str  # plaintext — shown exactly once


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    prefix: str
    scopes: list[str]
    rate_limit_rpm: int
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime
