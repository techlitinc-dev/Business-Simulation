"""Unit tests for scenario_service (T42)."""

import json
from pathlib import Path

import pytest
from app.core.exceptions import DomainError
from app.db.base import Base
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.scenario import Scenario
from app.models.workspace import Workspace
from app.schemas.blueprint import BlueprintPayload
from app.services import scenario_service
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


@pytest.fixture
async def db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _workspace(db: AsyncSession, name: str = "W") -> Workspace:
    ws = Workspace(name=name, slug=f"{name.lower()}-1234", plan_tier="free")
    db.add(ws)
    await db.commit()
    return ws


async def _blueprint_with_version(
    db: AsyncSession, ws: Workspace, payload: dict
) -> BlueprintVersion:
    bp = Blueprint(
        workspace_id=ws.id,
        name="Source BP",
        industry="B2B SaaS",
        stage="Seed",
        current_version=1,
    )
    db.add(bp)
    await db.flush()
    version = BlueprintVersion(
        blueprint_id=bp.id, version=1, payload=payload
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version


async def test_publish_validates_and_stores_payload(db: AsyncSession) -> None:
    ws = await _workspace(db, "Pub")
    version = await _blueprint_with_version(db, ws, _valid_payload())

    scenario = await scenario_service.publish(
        db,
        workspace_id=ws.id,
        title="2008 Crash",
        description="A market crash scenario",
        category="market_crash",
        blueprint_version_id=version.id,
    )
    assert scenario.id.startswith("scn_")
    assert scenario.payload == BlueprintPayload.model_validate(_valid_payload())


async def test_publish_foreign_version_404(db: AsyncSession) -> None:
    ws = await _workspace(db, "Pub2")
    other_ws = await _workspace(db, "Other")
    version = await _blueprint_with_version(db, other_ws, _valid_payload())

    with pytest.raises(DomainError) as exc:
        await scenario_service.publish(
            db,
            workspace_id=ws.id,
            title="X",
            description="Y",
            category="custom",
            blueprint_version_id=version.id,
        )
    assert exc.value.status_code == 404


async def test_list_public_filters_by_category(db: AsyncSession) -> None:
    ws = await _workspace(db, "List")
    version = await _blueprint_with_version(db, ws, _valid_payload())
    await scenario_service.publish(
        db, workspace_id=ws.id, title="Crash", description="D", category="market_crash",
        blueprint_version_id=version.id,
    )
    await scenario_service.publish(
        db, workspace_id=ws.id, title="Pandemic", description="D", category="pandemic",
        blueprint_version_id=version.id,
    )

    items, total = await scenario_service.list_public(db, category="market_crash")
    assert total == 1
    assert items[0].title == "Crash"


async def test_clone_creates_blueprint_and_increments_count(db: AsyncSession) -> None:
    ws = await _workspace(db, "Clone")
    target = await _workspace(db, "Target")
    version = await _blueprint_with_version(db, ws, _valid_payload())
    scenario = await scenario_service.publish(
        db, workspace_id=ws.id, title="Clone Me", description="D", category="custom",
        blueprint_version_id=version.id,
    )

    bp, new_version = await scenario_service.clone_to_workspace(db, scenario.id, target.id)
    assert bp.workspace_id == target.id
    assert bp.name == "Clone Me"
    assert new_version.version == 1
    assert new_version.payload == _valid_payload()

    # Second clone increments to 2.
    await scenario_service.clone_to_workspace(db, scenario.id, target.id)
    refreshed = await db.get(Scenario, scenario.id)
    assert refreshed.clones_count == 2


async def test_unpublish_non_author_403(db: AsyncSession) -> None:
    ws = await _workspace(db, "Auth")
    other = await _workspace(db, "Other")
    version = await _blueprint_with_version(db, ws, _valid_payload())
    scenario = await scenario_service.publish(
        db, workspace_id=ws.id, title="S", description="D", category="custom",
        blueprint_version_id=version.id,
    )

    with pytest.raises(DomainError) as exc:
        await scenario_service.unpublish(
            db, scenario.id, actor_workspace_id=other.id
        )
    assert exc.value.status_code == 403

    await scenario_service.unpublish(db, scenario.id, actor_workspace_id=ws.id)
    refreshed = await db.get(Scenario, scenario.id)
    assert refreshed.is_public is False
