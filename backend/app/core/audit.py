"""Audit log middleware — records mutating API requests (T49)."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import Request

logger = structlog.get_logger("forge.audit")

#: Paths that are never audited (probes + metrics).
_SKIP_PATHS = {"/metrics", "/health", "/ready"}

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


async def _write_audit_row(
    *,
    request_id: str | None,
    user_id: Any,
    workspace_id: Any,
    method: str,
    path: str,
    status_code: int,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    """Persist one audit row via an independent session (never breaks request)."""
    from app.db.session import async_session_factory
    from app.models.audit_log import AuditLog

    async with async_session_factory() as session:
        session.add(
            AuditLog(
                request_id=request_id,
                user_id=user_id,
                workspace_id=workspace_id,
                method=method,
                path=path,
                status_code=status_code,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        await session.commit()


async def audit_log_middleware(request: Request, call_next: Any) -> Any:
    """Record every mutating /api/v1 request after the response is produced.

    Runs after the inner handler so ``status_code`` is final. Writes go
    through an independent async session so a DB failure is logged but never
    changes the response. Skips probes, metrics, and WebSocket upgrades.

    Disabled entirely in the test environment (``settings.testing``) so the
    suite's shared in-memory SQLite session isn't disturbed; the dedicated
    audit tests flip it back on.
    """
    from app.core.config import get_settings

    if get_settings().testing:
        return await call_next(request)

    path = request.url.path
    method = request.method.upper()

    is_ws = path.startswith("/ws/") or request.scope.get("type") == "websocket"
    if (
        method not in _MUTATING_METHODS
        or path in _SKIP_PATHS
        or is_ws
        or not path.startswith("/api/v1/")
    ):
        return await call_next(request)

    response = await call_next(request)

    # Resolve the authenticated caller (JWT or API key) for attribution.
    user_id = None
    workspace_id = None
    try:
        from uuid import UUID

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            # Best-effort: decode the token and look up the user.
            from app.core.security import decode_token
            from app.db.session import async_session_factory

            token = auth_header.split(" ", 1)[1]
            try:
                payload = decode_token(token)
                sub = payload.get("sub")
                if sub:
                    async with async_session_factory() as session:
                        from app.models.user import User

                        user = await session.get(User, UUID(sub))
                        if user is not None:
                            user_id = user.id
            except Exception:  # noqa: BLE001 - attribution is best-effort
                pass
    except Exception:  # noqa: BLE001
        pass

    forwarded = request.headers.get("X-Forwarded-For")
    ip_address = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else None
    )

    try:
        await _write_audit_row(
            request_id=response.headers.get("X-Request-ID"),
            user_id=user_id,
            workspace_id=workspace_id,
            method=method,
            path=path,
            status_code=response.status_code,
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception:  # noqa: BLE001 - audit failure never breaks the request
        logger.warning("audit log write failed", path=path, method=method)

    return response
