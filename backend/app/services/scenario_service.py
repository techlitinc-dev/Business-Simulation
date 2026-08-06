"""Scenario marketplace business logic (T42)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.scenario import Scenario
from app.schemas.blueprint import BlueprintPayload
from app.schemas.scenario import ScenarioResponse, ScenarioSummary


async def _get_version(
    db: AsyncSession, workspace_id: uuid.UUID, blueprint_version_id: str
) -> BlueprintVersion:
    """Load a blueprint version scoped to a workspace; 404 on any miss."""
    version = await db.scalar(
        select(BlueprintVersion)
        .join(BlueprintVersion.blueprint)
        .where(
            BlueprintVersion.id == blueprint_version_id,
            Blueprint.workspace_id == workspace_id,
        )
    )
    if version is None:
        raise DomainError(status_code=404, detail="Blueprint version not found")
    return version


async def publish(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    title: str,
    description: str,
    category: str,
    blueprint_version_id: str,
) -> ScenarioResponse:
    version = await _get_version(db, workspace_id, blueprint_version_id)
    payload = BlueprintPayload.model_validate(dict(version.payload))

    scenario = Scenario(
        author_workspace_id=workspace_id,
        title=title.strip(),
        description=description.strip(),
        category=category,
        payload=payload.model_dump(mode="json"),
    )
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)
    return _to_response(scenario)


def _to_response(scenario: Scenario) -> ScenarioResponse:
    return ScenarioResponse(
        id=scenario.id,
        title=scenario.title,
        description=scenario.description,
        category=scenario.category,
        clones_count=scenario.clones_count,
        is_featured=scenario.is_featured,
        created_at=scenario.created_at,
        payload=BlueprintPayload.model_validate(dict(scenario.payload)),
        author_workspace_id=str(scenario.author_workspace_id),
    )


async def list_public(
    db: AsyncSession,
    *,
    category: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ScenarioSummary], int]:
    query = select(Scenario).where(Scenario.is_public.is_(True))
    count_query = select(func.count()).select_from(Scenario).where(
        Scenario.is_public.is_(True)
    )
    if category:
        query = query.where(Scenario.category == category)
        count_query = count_query.where(Scenario.category == category)

    total = int(await db.scalar(count_query) or 0)
    rows = await db.scalars(
        query.order_by(Scenario.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [ScenarioSummary.model_validate(s) for s in rows], total


async def list_featured(db: AsyncSession) -> list[ScenarioSummary]:
    rows = await db.scalars(
        select(Scenario)
        .where(Scenario.is_public.is_(True), Scenario.is_featured.is_(True))
        .order_by(Scenario.created_at.desc())
    )
    return [ScenarioSummary.model_validate(s) for s in rows]


async def get(
    db: AsyncSession, scenario_id: str, *, viewer_workspace_id: uuid.UUID | None = None
) -> Scenario:
    scenario = await db.get(Scenario, scenario_id)
    if scenario is None:
        raise DomainError(status_code=404, detail="Scenario not found")
    if not scenario.is_public and viewer_workspace_id is None:
        raise DomainError(status_code=404, detail="Scenario not found")
    if (
        not scenario.is_public
        and viewer_workspace_id is not None
        and scenario.author_workspace_id != viewer_workspace_id
    ):
        raise DomainError(status_code=404, detail="Scenario not found")
    return scenario


async def clone_to_workspace(
    db: AsyncSession,
    scenario_id: str,
    workspace_id: uuid.UUID,
) -> tuple[Blueprint, BlueprintVersion]:
    """Copy a scenario's payload into a new Blueprint + v1 in the caller's ws."""
    scenario = await db.get(Scenario, scenario_id)
    if scenario is None or not scenario.is_public:
        raise DomainError(status_code=404, detail="Scenario not found")

    payload = BlueprintPayload.model_validate(dict(scenario.payload))
    blueprint = Blueprint(
        workspace_id=workspace_id,
        name=scenario.title,
        industry=payload.business_profile.industry,
        stage=payload.business_profile.stage,
        current_version=1,
    )
    db.add(blueprint)
    await db.flush()
    version = BlueprintVersion(
        blueprint_id=blueprint.id,
        version=1,
        payload=payload.model_dump(mode="json"),
    )
    db.add(version)

    scenario.clones_count += 1
    await db.commit()
    await db.refresh(blueprint)
    return blueprint, version


async def unpublish(
    db: AsyncSession,
    scenario_id: str,
    *,
    actor_workspace_id: uuid.UUID,
    is_admin: bool = False,
) -> Scenario:
    scenario = await db.get(Scenario, scenario_id)
    if scenario is None:
        raise DomainError(status_code=404, detail="Scenario not found")
    if not is_admin and scenario.author_workspace_id != actor_workspace_id:
        raise DomainError(status_code=403, detail="Only the author can unpublish")
    scenario.is_public = False
    await db.commit()
    await db.refresh(scenario)
    return scenario


async def delete(
    db: AsyncSession,
    scenario_id: str,
    *,
    actor_workspace_id: uuid.UUID,
    is_admin: bool = False,
) -> None:
    scenario = await db.get(Scenario, scenario_id)
    if scenario is None:
        raise DomainError(status_code=404, detail="Scenario not found")
    if not is_admin and scenario.author_workspace_id != actor_workspace_id:
        raise DomainError(status_code=403, detail="Only the author can delete")
    await db.delete(scenario)
    await db.commit()
