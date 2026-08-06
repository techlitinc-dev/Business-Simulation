"""Domain exceptions and FastAPI exception handlers."""


import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger("forge.exceptions")


class DomainError(Exception):
    """Expected application error mapped to an HTTP response."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class StructuredOutputError(Exception):
    """Raised when an LLM fails to produce schema-valid JSON after repairs."""

    def __init__(self, raw_output: str, validation_error: Exception) -> None:
        self.raw_output = raw_output
        self.validation_error = validation_error
        super().__init__(f"LLM returned invalid structured output: {validation_error}")


class PlanLimitExceeded(Exception):
    """Raised when a workspace exceeds its plan limit (T41)."""

    def __init__(self, metric: str, limit: int, used: int, tier: str) -> None:
        self.metric = metric
        self.limit = limit
        self.used = used
        self.tier = tier
        super().__init__(
            f"Plan limit exceeded for {metric}: used {used}, limit {limit} (tier {tier})"
        )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(PlanLimitExceeded)
    async def plan_limit_handler(request: Request, exc: PlanLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=402,
            content={
                "detail": (
                    f"Plan limit exceeded: {exc.used}/{exc.limit} {exc.metric} used "
                    f"this month (tier: {exc.tier})"
                ),
                "code": "plan_limit_exceeded",
                "metric": exc.metric,
                "limit": exc.limit,
                "used": exc.used,
                "tier": exc.tier,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Logged via structlog; the client never sees the traceback.
        logger.exception("unhandled error", path=request.url.path, exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
