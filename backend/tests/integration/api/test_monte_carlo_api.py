"""Integration tests for Monte Carlo mode (T27)."""

import json
from pathlib import Path

from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _owner(client: AsyncClient, email: str = "mc-owner@b.co"):
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "McOwner", "password": "password123"},
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


async def test_monte_carlo_run_completes_with_result(
    client: AsyncClient, monkeypatch
) -> None:
    import fakeredis.aioredis

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    resp = await client.post(
        "/api/v1/blueprints",
        json={
            "name": "MC BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
        headers=owner["headers"],
    )
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=owner["headers"])
    version_id = versions.json()[0]["id"]

    start = await client.post(
        "/api/v1/simulations",
        json={
            "blueprint_version_id": version_id,
            "mode": "monte_carlo",
            "seed": 42,
            "config": {"months": 24, "n_runs": 10},
        },
        headers=owner["headers"],
    )
    assert start.status_code == 201
    run_id = start.json()["id"]
    assert start.json()["status"] == "pending"

    # Eager Celery (conftest) runs the task inline; the GET merges progress.
    get = await client.get(f"/api/v1/simulations/{run_id}", headers=owner["headers"])
    body = get.json()
    assert body["status"] == "completed"
    assert body["result"]["n_runs"] == 10
    assert 0 <= body["result"]["survival_rate"] <= 1
    assert body["result"]["median_lifespan_months"] <= 24
    failed = sum(
        1 for s in body["result"]["runs_summary"] if not s["survived"]
    )
    assert sum(body["result"]["kill_vectors"].values()) == failed


async def test_monte_carlo_determinism(client: AsyncClient, monkeypatch) -> None:
    import fakeredis.aioredis

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    resp = await client.post(
        "/api/v1/blueprints",
        json={
            "name": "MC BP2",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
        headers=owner["headers"],
    )
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=owner["headers"])
    version_id = versions.json()[0]["id"]

    runs = []
    for _ in range(2):
        start = await client.post(
            "/api/v1/simulations",
            json={
                "blueprint_version_id": version_id,
                "mode": "monte_carlo",
                "seed": 7,
                "config": {"months": 24, "n_runs": 5},
            },
            headers=owner["headers"],
        )
        run_id = start.json()["id"]
        get = await client.get(f"/api/v1/simulations/{run_id}", headers=owner["headers"])
        runs.append(get.json()["result"])

    assert runs[0] == runs[1]
