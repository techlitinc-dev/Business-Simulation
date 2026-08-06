"""Billing request/response schemas (T40/T41)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tier: Literal["pro", "enterprise"]


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tier: str
    status: str
    current_period_end: datetime | None = None


class UsageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tier: str
    period: str
    usage: dict[str, int]
    limits: dict[str, int]
