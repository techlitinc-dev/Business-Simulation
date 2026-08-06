"""Admin endpoints (T46) — require_admin only."""

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, DbSession
from app.schemas.admin import (
    AdminStatsResponse,
    AdminUserListResponse,
    AdminWorkspaceListResponse,
    AuditLogItem,
    AuditLogListResponse,
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


@router.get("/audit-log", response_model=AuditLogListResponse)
async def audit_log(
    db: DbSession,
    _admin: AdminUser,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    user_id: str | None = Query(default=None),
    path: str | None = Query(default=None),
) -> AuditLogListResponse:
    """Retrieve audit-log rows (T49) — admin only."""
    rows, total = await admin_service.admin_audit_logs(
        db, page=page, user_id=user_id, path=path, limit=limit
    )
    items = [
        AuditLogItem(
            id=row.id,
            created_at=row.created_at,
            request_id=row.request_id,
            user_id=str(row.user_id) if row.user_id else None,
            workspace_id=str(row.workspace_id) if row.workspace_id else None,
            method=row.method,
            path=row.path,
            status_code=row.status_code,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
        )
        for row in rows
    ]
    return AuditLogListResponse(items=items, total=total, page=page)
