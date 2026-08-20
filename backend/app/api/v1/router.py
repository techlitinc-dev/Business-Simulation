"""API v1 router — aggregates all endpoint modules."""

from fastapi import APIRouter

from app.core.config import get_settings

from .endpoints import (
    actuals,
    admin,
    advisory,
    api_keys,
    auth,
    billing,
    blueprints,
    copilot,
    deep_report,
    leaderboard,
    reports,
    scenarios,
    simulations,
    users,
    webhooks,
    whatif,
    workspaces,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(workspaces.router)
api_router.include_router(blueprints.router)
api_router.include_router(simulations.router)
api_router.include_router(reports.router)
api_router.include_router(deep_report.router)
api_router.include_router(billing.router)
api_router.include_router(webhooks.router)
api_router.include_router(scenarios.router)
api_router.include_router(leaderboard.router)
api_router.include_router(api_keys.router)
api_router.include_router(admin.router)
api_router.include_router(whatif.router)
api_router.include_router(actuals.router)
api_router.include_router(advisory.router)
api_router.include_router(copilot.router)


@api_router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version}
