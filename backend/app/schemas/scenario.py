"""Scenario request/response schemas (T42)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.blueprint import BlueprintPayload

_HTML_TAG_RE = re.compile(r"<[^>]*>")


class ScenarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    category: Literal[
        "market_crash",
        "competitor_attack",
        "supply_chain",
        "regulatory",
        "pandemic",
        "custom",
    ]
    blueprint_version_id: str = Field(min_length=1)

    @field_validator("title", "description")
    @classmethod
    def strip_html(cls, value: str) -> str:
        """Reject HTML/script payloads — marketplace fields are plain text."""
        stripped = _HTML_TAG_RE.sub("", value).strip()
        if not stripped:
            raise ValueError("must not contain only HTML tags")
        return stripped


class ScenarioSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    category: str
    clones_count: int
    is_featured: bool
    created_at: datetime


class ScenarioResponse(ScenarioSummary):
    payload: BlueprintPayload
    author_workspace_id: str


class ScenarioListResponse(BaseModel):
    items: list[ScenarioSummary]
    total: int
    page: int


class CloneResponse(BaseModel):
    blueprint_id: str
    blueprint_version_id: str
