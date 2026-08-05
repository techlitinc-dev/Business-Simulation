"""Integration tests for run controls pause/resume/cancel (T28)."""

import json
from pathlib import Path

import fakeredis.aioredis
from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _owner(client: AsyncClient, email: str = "ctl-owner@b.co"):
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "CtlOwner", "password": "password123"},
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
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws["id"]},
    }


async def _start_stress(client: AsyncClient, headers: dict, seed: int = 42) -> dict:
    resp = await client.post(
        "/api/v1/blueprints",
        json={
            "name": "Ctrl BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
        headers=headers,
    )
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=headers)
    version_id = versions.json()[0]["id"]
    run = await client.post(
        "/api/v1/simulations",
        json={"blueprint_version_id": version_id, "mode": "stress", "seed": seed},
        headers=headers,
    )
    return run.json()


async def test_pause_resume_cancel_cycle(client: AsyncClient, monkeypatch) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    run = await _start_stress(client, owner["headers"])
    run_id = run["id"]
    assert run["status"] == "awaiting_decision"

    pause = await client.post(
        f"/api/v1/simulations/{run_id}/control",
        json={"action": "pause"},
        headers=owner["headers"],
    )
    assert pause.status_code == 200
    assert pause.json()["status"] == "paused"

    resume = await client.post(
        f"/api/v1/simulations/{run_id}/control",
        json={"action": "resume"},
        headers=owner["headers"],
    )
    assert resume.status_code == 200
    assert resume.json()["status"] == "awaiting_decision"

    cancel = await client.post(
        f"/api/v1/simulations/{run_id}/control",
        json={"action": "cancel"},
        headers=owner["headers"],
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    # Second cancel on a terminal run -> 409.
    again = await client.post(
        f"/api/v1/simulations/{run_id}/control",
        json={"action": "cancel"},
        headers=owner["headers"],
    )
    assert again.status_code == 409


async def test_pause_on_non_running_409(client: AsyncClient, monkeypatch) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    run = await _start_stress(client, owner["headers"])

    # Cancel first, then pause -> 409.
    await client.post(
        f"/api/v1/simulations/{run['id']}/control",
        json={"action": "cancel"},
        headers=owner["headers"],
    )
    resp = await client.post(
        f"/api/v1/simulations/{run['id']}/control",
        json={"action": "pause"},
        headers=owner["headers"],
    )
    assert resp.status_code == 409
