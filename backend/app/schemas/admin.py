"""Admin schemas (T46)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminStatsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_users: int
    users_last_30d: int
    total_workspaces: int
    workspaces_last_30d: int
    subscriptions_by_tier: dict[str, int]
    mrr_estimate_usd: int
    runs_this_month: int
    monte_carlo_ticks_this_month: int
    llm_tokens_this_month: int


class AdminUserItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: str
    name: str
    is_admin: bool
    is_verified: bool
    created_at: datetime
    workspace_count: int


class AdminUserListResponse(BaseModel):
    items: list[AdminUserItem]
    total: int
    page: int


class AdminWorkspaceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    slug: str
    plan_tier: str
    member_count: int
    runs_count: int
    created_at: datetime


class AdminWorkspaceListResponse(BaseModel):
    items: list[AdminWorkspaceItem]
    total: int
    page: int
