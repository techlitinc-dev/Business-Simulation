"""Rate limiting (T45 per-key + T49 global).

Two mechanisms, both in-process sliding windows (no external storage):

1. ``api_key_rate_limit_middleware`` — per-X-API-Key window (T45), keyed by the
   key's 12-char prefix.
2. ``global_rate_limit_middleware`` — per-remote-address window (T49), with a
   configurable default plus stricter per-route auth limits. Skipped entirely
   when ``settings.testing`` is set so the test suite runs freely; dedicated
   rate-limit tests flip it back on via ``settings.testing = False``.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings

#: prefix -> deque of request timestamps (in-memory, per-process).
_WINDOWS: dict[str, deque[float]] = defaultdict(deque)

#: remote-address -> deque of timestamps for the global limiter (T49).
_GLOBAL_WINDOWS: dict[str, deque[float]] = defaultdict(deque)

#: seconds of a rate-limit window.
_WINDOW_SECONDS = 60.0

#: paths that are never rate-limited (probes).
_UNLIMITED_PATHS = {"/metrics", "/health", "/ready"}


def reset_windows() -> None:
    """Clear all rate-limit windows (tests)."""
    _WINDOWS.clear()
    _GLOBAL_WINDOWS.clear()


def _bucket_key(request: Request) -> tuple[str, int] | None:
    """Return (bucket, rpm) when the request carries an X-API-Key, else None."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    prefix = api_key[:12]
    return prefix, 0  # rpm resolved from the key at check time


def _hit(window: deque[float], rpm: int) -> bool:
    """Record a hit; return False (rejected) when the window is full."""
    now = time.monotonic()
    while window and now - window[0] > _WINDOW_SECONDS:
        window.popleft()
    if len(window) >= rpm:
        return False
    window.append(now)
    return True


def _remote_addr(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def api_key_rate_limit_middleware(request: Request, call_next: Any) -> Any:
    """Reject the request with 429 once a key exceeds its rpm window."""
    key_header = request.headers.get("X-API-Key")
    if key_header:
        from sqlalchemy import select

        from app.db.session import async_session_factory
        from app.models.api_key import ApiKey

        prefix = key_header[:12]
        async with async_session_factory() as session:
            key = await session.scalar(
                select(ApiKey).where(
                    ApiKey.prefix == prefix, ApiKey.revoked_at.is_(None)
                )
            )
            rpm = key.rate_limit_rpm if key is not None else 60

        window = _WINDOWS[prefix]
        if not _hit(window, rpm):
            now = time.monotonic()
            retry_after = max(1, int(_WINDOW_SECONDS - (now - (window[0] if window else now))))
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )

    return await call_next(request)


def _route_limit_for(request: Request) -> int | None:
    """Return a stricter per-route limit (rpm) for auth endpoints, else None."""
    settings = get_settings()
    path = request.url.path
    method = request.method.upper()
    if method == "POST":
        if path in ("/api/v1/auth/login", "/api/v1/auth/forgot-password"):
            return _parse_rpm(settings.rate_limit_auth)
        if path == "/api/v1/auth/register":
            return _parse_rpm(settings.rate_limit_register)
    return None


def _parse_rpm(limit_str: str) -> int:
    """Parse a ``"N/minute"`` style limit string to N."""
    try:
        return int(limit_str.split("/")[0])
    except (ValueError, IndexError):
        return 100


async def global_rate_limit_middleware(request: Request, call_next: Any) -> Any:
    """Apply the global default + stricter auth limits per remote address (T49).

    Disabled when ``settings.testing`` is true (the test suite), except in the
    dedicated rate-limit tests that flip it back on.
    """
    settings = get_settings()
    if settings.testing:
        return await call_next(request)

    if request.url.path in _UNLIMITED_PATHS:
        return await call_next(request)

    rpm = _route_limit_for(request) or _parse_rpm(settings.rate_limit_default)
    key = f"{_remote_addr(request)}|{rpm}"
    window = _GLOBAL_WINDOWS[key]
    if not _hit(window, rpm):
        return JSONResponse(
            status_code=429,
            content={"detail": "rate limit exceeded"},
        )

    return await call_next(request)
