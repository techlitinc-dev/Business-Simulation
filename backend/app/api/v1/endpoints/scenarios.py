"""Scenario marketplace endpoints (T42)."""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import (
    CurrentUser,
    CurrentWorkspace,
    DbSession,
    OptionalUser,
)
from app.core.exceptions import DomainError
from app.schemas.scenario import (
    CloneResponse,
    ScenarioCreate,
    ScenarioListResponse,
    ScenarioResponse,
    ScenarioSummary,
)
from app.services import scenario_service

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


def _handle(exc: DomainError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_scenario(
    payload: ScenarioCreate,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> ScenarioResponse:
    try:
        return await scenario_service.publish(
            db,
            workspace_id=workspace.id,
            title=payload.title,
            description=payload.description,
            category=payload.category,
            blueprint_version_id=payload.blueprint_version_id,
        )
    except DomainError as exc:
        raise _handle(exc) from exc


@router.get("", response_model=ScenarioListResponse)
async def list_scenarios(
    db: DbSession,
    category: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
) -> ScenarioListResponse:
    items, total = await scenario_service.list_public(db, category=category, page=page)
    return ScenarioListResponse(items=items, total=total, page=page)


@router.get("/featured", response_model=list[ScenarioSummary])
async def featured_scenarios(db: DbSession) -> list[ScenarioSummary]:
    return await scenario_service.list_featured(db)


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: str,
    db: DbSession,
    user: OptionalUser,
) -> ScenarioResponse:
    viewer = None
    if user is not None:
        from sqlalchemy import select

        from app.models.workspace import Membership

        membership = await db.scalar(
            select(Membership).where(Membership.user_id == user.id)
        )
        viewer = membership.workspace_id if membership is not None else None
    try:
        scenario = await scenario_service.get(
            db, scenario_id, viewer_workspace_id=viewer
        )
    except DomainError as exc:
        raise _handle(exc) from exc
    return scenario_service._to_response(scenario)


@router.post("/{scenario_id}/clone", status_code=status.HTTP_201_CREATED)
async def clone_scenario(
    scenario_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> CloneResponse:
    try:
        blueprint, version = await scenario_service.clone_to_workspace(
            db, scenario_id, workspace.id
        )
    except DomainError as exc:
        raise _handle(exc) from exc
    return CloneResponse(blueprint_id=blueprint.id, blueprint_version_id=version.id)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: str,
    db: DbSession,
    user: CurrentUser,
    workspace: CurrentWorkspace,
) -> None:
    try:
        await scenario_service.delete(
            db,
            scenario_id,
            actor_workspace_id=workspace.id,
            is_admin=bool(user.is_admin),
        )
    except DomainError as exc:
        raise _handle(exc) from exc
    return None
