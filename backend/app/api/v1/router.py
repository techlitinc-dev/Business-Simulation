"""API v1 router — aggregates all endpoint modules."""

from fastapi import APIRouter

from app.core.config import get_settings

from .endpoints import (
    actuals,
    admin,
    advisory,
    api_keys,
    auth,
    benchmark,
    billing,
    blueprints,
    comments,
    copilot,
    dataroom,
    deep_report,
    export,
    gamification,
    industry_packs,
    integrations,
    investor,
    journal,
    leaderboard,
    portfolio,
    reports,
    scenarios,
    scim,
    simulations,
    sso,
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
api_router.include_router(benchmark.router)
api_router.include_router(investor.router)
api_router.include_router(dataroom.router)
api_router.include_router(portfolio.router)
api_router.include_router(sso.router)
api_router.include_router(scim.router)
api_router.include_router(journal.router)
api_router.include_router(comments.router)
api_router.include_router(export.router)
api_router.include_router(integrations.router)
api_router.include_router(gamification.router)
api_router.include_router(industry_packs.router)


@api_router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version}
