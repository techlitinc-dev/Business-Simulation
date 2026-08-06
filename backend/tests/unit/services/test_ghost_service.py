"""Integration tests for Ghost Mode (T43) — deterministic mock provider only."""

import json
from pathlib import Path

from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _register(client: AsyncClient, email: str) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Ghost", "password": "password123"},
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


async def _create_blueprint_version(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/blueprints",
        headers=headers,
        json={
            "name": "Ghost BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
    )
    assert resp.status_code == 201, resp.text
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=headers)
    return versions.json()[0]["id"]


async def test_ghost_run_completes_without_decide_calls(client: AsyncClient) -> None:
    account = await _register(client, "ghost1@b.co")
    bpv = await _create_blueprint_version(client, account["headers"])

    resp = await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={
            "blueprint_version_id": bpv,
            "mode": "ghost",
            "config": {"personality": "aggressive"},
            "seed": 42,
        },
    )
    assert resp.status_code == 201, resp.text
    run = resp.json()
    assert run["mode"] == "ghost"
    assert run["status"] in ("completed", "dead")
    assert run["current_month"] >= 1


async def test_ghost_run_missing_personality_422(client: AsyncClient) -> None:
    account = await _register(client, "ghost2@b.co")
    bpv = await _create_blueprint_version(client, account["headers"])

    resp = await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={"blueprint_version_id": bpv, "mode": "ghost"},
    )
    assert resp.status_code == 422


async def test_ghost_run_invalid_personality_422(client: AsyncClient) -> None:
    account = await _register(client, "ghost3@b.co")
    bpv = await _create_blueprint_version(client, account["headers"])

    resp = await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={
            "blueprint_version_id": bpv,
            "mode": "ghost",
            "config": {"personality": "reckless"},
        },
    )
    assert resp.status_code == 422


async def test_ghost_deterministic_same_seed(client: AsyncClient) -> None:
    account = await _register(client, "ghost4@b.co")
    bpv = await _create_blueprint_version(client, account["headers"])

    async def run_ghost():
        resp = await client.post(
            "/api/v1/simulations",
            headers=account["headers"],
            json={
                "blueprint_version_id": bpv,
                "mode": "ghost",
                "config": {"personality": "conservative"},
                "seed": 99,
            },
        )
        return resp

    r1 = await run_ghost()
    r2 = await run_ghost()
    assert r1.status_code == r2.status_code == 201
    run1 = r1.json()
    run2 = r2.json()
    assert run1["status"] == run2["status"]
    assert run1["current_month"] == run2["current_month"]

    # Final KPI traces identical (ignore per-row ids).
    ticks1 = (await client.get(
        f"/api/v1/simulations/{run1['id']}/ticks", headers=account["headers"]
    )).json()
    ticks2 = (await client.get(
        f"/api/v1/simulations/{run2['id']}/ticks", headers=account["headers"]
    )).json()
    strip = lambda rows: [(t["month"], t["kpis"]) for t in rows]  # noqa: E731
    assert strip(ticks1) == strip(ticks2)


async def test_ghost_decisions_tagged_with_actor(client: AsyncClient) -> None:
    account = await _register(client, "ghost5@b.co")
    bpv = await _create_blueprint_version(client, account["headers"])

    resp = await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={
            "blueprint_version_id": bpv,
            "mode": "ghost",
            "config": {"personality": "opportunist"},
            "seed": 7,
        },
    )
    run = resp.json()

    from app.db.session import async_session_factory
    from app.models.simulation import Decision
    from sqlalchemy import select

    async with async_session_factory() as session:
        rows = await session.execute(
            select(Decision).where(Decision.run_id == run["id"])
        )
        decisions = rows.scalars().all()

    for d in decisions:
        payload = d.projection or {}
        assert payload.get("actor") == "ghost"
        assert payload.get("personality") == "opportunist"
        assert payload.get("rationale")
