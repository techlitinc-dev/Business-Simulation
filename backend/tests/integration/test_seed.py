"""T50 seed script tests: idempotency + Format A validity."""

from app.db.session import async_session_factory
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.scenario import Scenario
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.blueprint import BlueprintPayload
from app.utils.seed import seed
from sqlalchemy import select


async def test_seed_is_idempotent_and_valid() -> None:
    async with async_session_factory() as session:
        await seed(session)

        # Counts after first run.
        users = (await session.scalars(select(User))).all()
        workspaces = (await session.scalars(select(Workspace))).all()
        blueprints = (await session.scalars(select(Blueprint))).all()
        scenarios = (await session.scalars(select(Scenario))).all()
        assert len(users) == 1
        assert len(workspaces) == 1
        assert workspaces[0].name == "Demo Ventures"
        assert len(blueprints) == 3
        assert len(scenarios) == 3

        # Every seeded payload validates against Format A.
        versions = (await session.scalars(select(BlueprintVersion))).all()
        assert len(versions) == 3
        for version in versions:
            BlueprintPayload.model_validate(dict(version.payload))

        # Second run → same counts (idempotent).
        await seed(session)
        users2 = (await session.scalars(select(User))).all()
        blueprints2 = (await session.scalars(select(Blueprint))).all()
        scenarios2 = (await session.scalars(select(Scenario))).all()
        assert len(users2) == len(users)
        assert len(blueprints2) == len(blueprints)
        assert len(scenarios2) == len(scenarios)

        # Exactly one completed baseline run with ticks.
        from app.models.simulation import SimulationRun, TickLog
        from sqlalchemy import func

        runs = (await session.scalars(select(SimulationRun))).all()
        assert len(runs) == 1
        assert runs[0].status == "completed"
        assert runs[0].seed == 42
        tick_count = int(
            await session.scalar(select(func.count()).select_from(TickLog))
        )
        assert tick_count >= 12

        # Demo user can log in (password matches).
        from app.core.security import verify_password

        demo = (await session.scalars(select(User))).first()
        assert verify_password("demo-password-123", demo.pw_hash)

        # All 3 scenarios are public and authored by the demo workspace.
        assert all(s.is_public for s in scenarios)
        assert all(s.author_workspace_id == workspaces[0].id for s in scenarios)
