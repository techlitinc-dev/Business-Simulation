"""Integration tests for the simulation endpoints (T25)."""

import json
from pathlib import Path

from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _owner(client: AsyncClient, email: str = "sim-owner@b.co"):
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "SimOwner", "password": "password123"},
    )
    token = (
        await client.post(
            "/api/v1/auth/login", json={"email": email, "password": "password123"}
        )
    ).json()["access_token"]
    ws_resp = await client.get(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
    )
    ws = ws_resp.json()[0]
    return {
        "token": token,
        "workspace_id": ws["id"],
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws["id"]},
    }


async def _outsider(client: AsyncClient):
    return await _owner(client, "sim-outsider@b.co")


async def _create_blueprint(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/blueprints",
        json={
            "name": "Sim BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_start_baseline_returns_201_with_result(client: AsyncClient) -> None:
    owner = await _owner(client)
    bp_id = await _create_blueprint(client, owner["headers"])
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=owner["headers"])
    version_id = versions.json()[0]["id"]

    resp = await client.post(
        "/api/v1/simulations",
        json={
            "blueprint_version_id": version_id,
            "mode": "baseline",
            "seed": 42,
        },
        headers=owner["headers"],
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] in ("completed", "dead")
    assert body["seed"] == 42
    assert body["result"]["survived"] in (True, False)
    assert body["current_month"] >= 1

    ticks = await client.get(f"/api/v1/simulations/{body['id']}/ticks", headers=owner["headers"])
    assert ticks.status_code == 200
    assert len(ticks.json()) == body["current_month"]


async def test_start_without_seed_generates_one(client: AsyncClient) -> None:
    owner = await _owner(client)
    bp_id = await _create_blueprint(client, owner["headers"])
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=owner["headers"])
    version_id = versions.json()[0]["id"]

    resp = await client.post(
        "/api/v1/simulations",
        json={"blueprint_version_id": version_id, "mode": "baseline"},
        headers=owner["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["seed"] >= 0


async def test_cross_workspace_run_404(client: AsyncClient) -> None:
    owner = await _owner(client)
    outsider = await _outsider(client)
    bp_id = await _create_blueprint(client, owner["headers"])
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=owner["headers"])
    version_id = versions.json()[0]["id"]

    resp = await client.post(
        "/api/v1/simulations",
        json={"blueprint_version_id": version_id, "mode": "baseline", "seed": 1},
        headers=outsider["headers"],
    )
    assert resp.status_code == 404


async def test_get_run_404_for_outsider(client: AsyncClient) -> None:
    owner = await _owner(client)
    outsider = await _outsider(client)
    bp_id = await _create_blueprint(client, owner["headers"])
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=owner["headers"])
    version_id = versions.json()[0]["id"]
    run_id = (
        await client.post(
            "/api/v1/simulations",
            json={"blueprint_version_id": version_id, "mode": "baseline", "seed": 2},
            headers=owner["headers"],
        )
    ).json()["id"]

    resp = await client.get(f"/api/v1/simulations/{run_id}", headers=outsider["headers"])
    assert resp.status_code == 404


async def test_unauthenticated_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/simulations",
        json={"blueprint_version_id": "x", "mode": "baseline"},
    )
    assert resp.status_code == 401
