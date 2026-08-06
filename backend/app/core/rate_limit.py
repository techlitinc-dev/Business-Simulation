"""Per-key rate limiting middleware (T45).

Keys are bucketed by their 12-char prefix using an in-process sliding window.
A single-process dev/test default; Redis-backed limiting can be layered on
later without changing the middleware contract.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

#: prefix -> deque of request timestamps (in-memory, per-process).
_WINDOWS: dict[str, deque[float]] = defaultdict(deque)


def reset_windows() -> None:
    """Clear all rate-limit windows (tests)."""
    _WINDOWS.clear()


def _bucket_key(request: Request) -> tuple[str, int] | None:
    """Return (bucket, rpm) when the request carries an X-API-Key, else None."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    prefix = api_key[:12]
    return prefix, 0  # rpm resolved from the key at check time


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

        now = time.monotonic()
        window = _WINDOWS[prefix]
        # Drop entries older than 60s.
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= rpm:
            retry_after = max(1, int(60 - (now - (window[0] if window else now))))
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )
        window.append(now)

    return await call_next(request)
