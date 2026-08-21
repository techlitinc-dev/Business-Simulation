"""Webhook registration request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WebhookEvent = Literal["run.completed", "report.ready", "score.dropped"]


class WebhookCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    target_url: str = Field(min_length=1, max_length=512)
    events: list[WebhookEvent] = Field(min_length=1)


class WebhookCreatedResponse(BaseModel):
    id: str
    name: str
    target_url: str
    events: list[str]
    secret: str  # shown exactly once


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    target_url: str
    events: list[str]
    active: bool
    created_at: datetime
