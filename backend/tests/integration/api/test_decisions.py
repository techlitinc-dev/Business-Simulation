"""Integration tests for stress runs + decision endpoint (T26)."""

import json
from pathlib import Path

from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _owner(client: AsyncClient, email: str = "dec-owner@b.co"):
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "DecOwner", "password": "password123"},
    )
    token = (
        await client.post(
            "/api/v1/auth/login", json={"email": email, "password": "password123"}
        )
    ).json()["access_token"]
    resp = await client.get(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
    )
    ws = resp.json()[0]
    return {
        "token": token,
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws["id"]},
    }


async def _start_stress(client: AsyncClient, headers: dict, seed: int = 42) -> dict:
    resp = await client.post(
        "/api/v1/blueprints",
        json={
            "name": "Stress BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
        headers=headers,
    )
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=headers)
    version_id = versions.json()[0]["id"]

    run_resp = await client.post(
        "/api/v1/simulations",
        json={"blueprint_version_id": version_id, "mode": "stress", "seed": seed},
        headers=headers,
    )
    assert run_resp.status_code == 201
    return run_resp.json()


async def test_stress_run_returns_awaiting_decision(client: AsyncClient) -> None:
    owner = await _owner(client)
    run = await _start_stress(client, owner["headers"])
    assert run["status"] == "awaiting_decision"
    assert run["current_month"] >= 4


async def test_decide_endpoint_advances_run(client: AsyncClient) -> None:
    owner = await _owner(client)
    run = await _start_stress(client, owner["headers"])

    # Find the pending event via the WS-less API — use a fresh stress run's
    # events through the DB-backed helper instead.
    from app.db.session import async_session_factory
    from app.models.simulation import SimulationEvent
    from sqlalchemy import select

    async with async_session_factory() as session:
        event = (
            await session.scalars(
                select(SimulationEvent).where(SimulationEvent.run_id == run["id"])
            )
        ).first()
        event_id = event.id
        option_id = event.payload["strategic_options"][0]["option_id"]

    resp = await client.post(
        f"/api/v1/simulations/{run['id']}/decide",
        json={"event_id": event_id, "option_id": option_id},
        headers=owner["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision_id"].startswith("dec_")
    assert body["option_id"] == option_id
    assert body["run"]["status"] in ("awaiting_decision", "completed", "dead")
    assert body["run"]["current_month"] > run["current_month"]


async def test_decide_wrong_state_409(client: AsyncClient) -> None:
    owner = await _owner(client)
    run = await _start_stress(client, owner["headers"])

    from app.db.session import async_session_factory
    from app.models.simulation import SimulationEvent
    from sqlalchemy import select

    async with async_session_factory() as session:
        event = (
            await session.scalars(
                select(SimulationEvent).where(SimulationEvent.run_id == run["id"])
            )
        ).first()
        event_id = event.id
        option_id = event.payload["strategic_options"][0]["option_id"]

    # First decision succeeds.
    assert (
        await client.post(
            f"/api/v1/simulations/{run['id']}/decide",
            json={"event_id": event_id, "option_id": option_id},
            headers=owner["headers"],
        )
    ).status_code == 200

    # Second on the same event -> 409.
    resp = await client.post(
        f"/api/v1/simulations/{run['id']}/decide",
        json={"event_id": event_id, "option_id": option_id},
        headers=owner["headers"],
    )
    assert resp.status_code == 409


async def test_decide_unknown_option_422(client: AsyncClient) -> None:
    owner = await _owner(client)
    run = await _start_stress(client, owner["headers"])

    from app.db.session import async_session_factory
    from app.models.simulation import SimulationEvent
    from sqlalchemy import select

    async with async_session_factory() as session:
        event = (
            await session.scalars(
                select(SimulationEvent).where(SimulationEvent.run_id == run["id"])
            )
        ).first()

    resp = await client.post(
        f"/api/v1/simulations/{run['id']}/decide",
        json={"event_id": event.id, "option_id": "ZZZ"},
        headers=owner["headers"],
    )
    assert resp.status_code == 422
