"""API v1 router — aggregates all endpoint modules."""

from fastapi import APIRouter

from app.core.config import get_settings

from .endpoints import auth, blueprints, users, workspaces

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(workspaces.router)
api_router.include_router(blueprints.router)


@api_router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version}
