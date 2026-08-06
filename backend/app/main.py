"""FastAPI application factory for The Forge backend."""

from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints.ws import router as ws_router
from app.api.v1.router import api_router
from app.core.audit import audit_log_middleware
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import bind_request_id, setup_logging
from app.core.rate_limit import (
    api_key_rate_limit_middleware,
    global_rate_limit_middleware,
)

logger = structlog.get_logger("forge.main")


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(debug=settings.debug)

    app = FastAPI(title=settings.app_name, version=settings.app_version)

    # T48: Sentry — only when a DSN is configured; otherwise boot identically.
    if settings.sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[FastApiIntegration()],
            traces_sample_rate=settings.sentry_traces_sample_rate,
        )
        logger.info("sentry enabled")

    # T49: Strict CORS — origins from settings (never "*" with credentials).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # T48: request-ID — bind to logs + echo back in the response header.
    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = bind_request_id(request)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # T49: Security headers middleware.
    @app.middleware("http")
    async def security_headers_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    app.middleware("http")(api_key_rate_limit_middleware)
    app.middleware("http")(global_rate_limit_middleware)
    app.middleware("http")(audit_log_middleware)

    # T48: Prometheus metrics — /metrics, grouped by handler/method/status.
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    register_exception_handlers(app)
    app.include_router(api_router)
    app.include_router(ws_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": settings.app_version}

    @app.get("/ready")
    async def ready() -> JSONResponse:
        """Readiness probe: DB ``SELECT 1`` + Redis ``PING`` (T48)."""
        from redis.asyncio import Redis

        from app.db.session import async_session_factory

        checks: dict[str, str] = {}
        ok = True

        # DB
        try:
            async with async_session_factory() as session:
                from sqlalchemy import text

                result = await session.execute(text("SELECT 1"))
                if result.scalar() == 1:
                    checks["db"] = "ok"
                else:
                    checks["db"] = "error"
                    ok = False
        except Exception as exc:  # noqa: BLE001 - probe reports, never raises
            logger.warning("readiness: db check failed", exc_info=exc)
            checks["db"] = "error"
            ok = False

        # Redis — best-effort; the same client pattern workers use.
        try:
            redis = Redis.from_url(settings.redis_url, decode_responses=True)
            pong = await redis.ping()
            await redis.aclose()
            if pong:
                checks["redis"] = "ok"
            else:
                checks["redis"] = "error"
                ok = False
        except Exception as exc:  # noqa: BLE001
            logger.warning("readiness: redis check failed", exc_info=exc)
            checks["redis"] = "error"
            ok = False

        status = 200 if ok else 503
        return JSONResponse(
            status_code=status,
            content={"status": "ready" if ok else "not ready", "checks": checks},
        )

    logger.info("app started", version=settings.app_version)
    return app


app = create_app()
