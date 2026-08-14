"""Integration tests for the public leaderboard (T44)."""

import json
from pathlib import Path

from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _register(client: AsyncClient, email: str) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "LB", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    ws = (await client.get(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
    )).json()[0]
    return {
        "token": token,
        "workspace_id": ws["id"],
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws["id"]},
    }


async def _seed_completed_public_run(
    client: AsyncClient,
    account: dict,
    *,
    resilience_score: int,
    is_public: bool = True,
) -> str:
    import uuid

    from app.db.session import async_session_factory
    from app.models.blueprint import Blueprint, BlueprintVersion
    from app.models.simulation import SimulationRun
    from app.models.workspace import Workspace

    async with async_session_factory() as session:
        ws = await session.get(Workspace, uuid.UUID(account["workspace_id"]))
        bp = Blueprint(
            workspace_id=ws.id,
            name="LB Blueprint",
            industry="B2B SaaS",
            stage="Seed",
            current_version=1,
        )
        session.add(bp)
        await session.flush()
        version = BlueprintVersion(
            blueprint_id=bp.id, version=1, payload=_valid_payload()
        )
        session.add(version)
        await session.flush()
        run = SimulationRun(
            workspace_id=ws.id,
            blueprint_version_id=version.id,
            mode="monte_carlo",
            status="completed",
            seed=1,
            result={
                "resilience_score": resilience_score,
                "survival_rate": 0.5,
                "median_lifespan_months": 12,
            },
            is_public=is_public,
        )
        session.add(run)
        await session.commit()
        return run.id


async def test_leaderboard_requires_no_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/leaderboard")
    assert resp.status_code == 200
    assert resp.json() == {"entries": []}


async def test_leaderboard_orders_by_resilience_score(client: AsyncClient) -> None:
    account = await _register(client, "lb1@b.co")
    await _seed_completed_public_run(client, account, resilience_score=40)
    await _seed_completed_public_run(client, account, resilience_score=90)
    await _seed_completed_public_run(client, account, resilience_score=70)

    resp = await client.get("/api/v1/leaderboard")
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    scores = [e["resilience_score"] for e in entries]
    assert scores == sorted(scores, reverse=True)
    assert [e["rank"] for e in entries] == [1, 2, 3]
    # Runs without a shared report expose share_token=null (not an error).
    assert all(e["share_token"] is None for e in entries)


async def test_leaderboard_includes_share_token_when_report_shared(
    client: AsyncClient,
) -> None:
    account = await _register(client, "lb1b@b.co")
    run_id = await _seed_completed_public_run(
        client, account, resilience_score=60
    )

    from app.db.session import async_session_factory
    from app.models.report import Report

    async with async_session_factory() as session:
        session.add(
            Report(
                run_id=run_id,
                content_md="# Report",
                content_json={"survival": {"survival_rate": 0.5}},
                share_token="tok_abc123",
            )
        )
        await session.commit()

    entries = (await client.get("/api/v1/leaderboard")).json()["entries"]
    entry = next(e for e in entries if e["run_id"] == run_id)
    assert entry["share_token"] == "tok_abc123"


async def test_leaderboard_excludes_private_runs(client: AsyncClient) -> None:
    account = await _register(client, "lb2@b.co")
    await _seed_completed_public_run(client, account, resilience_score=90)
    await _seed_completed_public_run(
        client, account, resilience_score=95, is_public=False
    )

    resp = await client.get("/api/v1/leaderboard")
    entries = resp.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["resilience_score"] == 90


async def test_visibility_patch_toggles_public(client: AsyncClient) -> None:
    account = await _register(client, "lb3@b.co")
    run_id = await _seed_completed_public_run(
        client, account, resilience_score=50, is_public=False
    )

    resp = await client.patch(
        f"/api/v1/simulations/{run_id}",
        headers=account["headers"],
        json={"is_public": True},
    )
    assert resp.status_code == 200

    # Now appears on the leaderboard.
    entries = (await client.get("/api/v1/leaderboard")).json()["entries"]
    assert any(e["run_id"] == run_id for e in entries)


async def test_visibility_patch_requires_membership(client: AsyncClient) -> None:
    owner = await _register(client, "lb4@b.co")
    run_id = await _seed_completed_public_run(client, owner, resilience_score=50)

    outsider = await _register(client, "lb4b@b.co")
    resp = await client.patch(
        f"/api/v1/simulations/{run_id}",
        headers=outsider["headers"],
        json={"is_public": True},
    )
    assert resp.status_code == 403
