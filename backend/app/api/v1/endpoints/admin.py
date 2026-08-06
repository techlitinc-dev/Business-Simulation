"""Admin endpoints (T46) — require_admin only."""

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, DbSession
from app.schemas.admin import (
    AdminStatsResponse,
    AdminUserListResponse,
    AdminWorkspaceListResponse,
)
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsResponse, response_model_exclude_none=True)
async def stats(
    db: DbSession,
    _admin: AdminUser,
) -> AdminStatsResponse:
    return await admin_service.admin_stats(db)


@router.get("/users", response_model=AdminUserListResponse)
async def users(
    db: DbSession,
    _admin: AdminUser,
    page: int = Query(default=1, ge=1),
    q: str | None = Query(default=None),
) -> AdminUserListResponse:
    return await admin_service.admin_users(db, page=page, q=q)


@router.get("/workspaces", response_model=AdminWorkspaceListResponse)
async def workspaces(
    db: DbSession,
    _admin: AdminUser,
    page: int = Query(default=1, ge=1),
) -> AdminWorkspaceListResponse:
    return await admin_service.admin_workspaces(db, page=page)
