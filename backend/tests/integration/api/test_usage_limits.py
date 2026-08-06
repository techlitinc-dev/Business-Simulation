"""Integration tests for usage metering + plan-limit enforcement (T41)."""

import json
from pathlib import Path

from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _register(client: AsyncClient, email: str) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Usage", "password": "password123"},
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


async def _create_blueprint(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/blueprints",
        headers=headers,
        json={
            "name": "Usage BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
    )
    assert resp.status_code == 201, resp.text
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=headers)
    return versions.json()[0]["id"]


async def _set_plan_tier(client: AsyncClient, ws_id: str, tier: str) -> None:
    import uuid

    from app.db.session import async_session_factory
    from app.models.workspace import Workspace

    async with async_session_factory() as session:
        workspace = await session.get(Workspace, uuid.UUID(ws_id))
        workspace.plan_tier = tier
        await session.commit()


async def test_usage_endpoint_returns_counters_and_limits(
    client: AsyncClient,
) -> None:
    account = await _register(client, "usage1@b.co")
    resp = await client.get(
        "/api/v1/billing/usage", headers=account["headers"]
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "free"
    assert body["usage"] == {"runs_used": 0, "mc_ticks_used": 0, "llm_tokens_used": 0}
    assert body["limits"]["runs_per_month"] == 3
    assert body["limits"]["monte_carlo_runs_per_batch"] == 25
    assert body["limits"]["llm_tokens_per_month"] == 50_000


async def test_starting_run_increments_runs_used(client: AsyncClient) -> None:
    account = await _register(client, "usage2@b.co")
    bp = await _create_blueprint(client, account["headers"])

    resp = await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={"blueprint_version_id": bp, "mode": "baseline"},
    )
    assert resp.status_code == 201, resp.text

    usage = (await client.get(
        "/api/v1/billing/usage", headers=account["headers"]
    )).json()
    assert usage["usage"]["runs_used"] == 1


async def test_free_workspace_blocked_at_3_runs(client: AsyncClient) -> None:
    account = await _register(client, "usage3@b.co")
    bp = await _create_blueprint(client, account["headers"])

    for _ in range(3):
        resp = await client.post(
            "/api/v1/simulations",
            headers=account["headers"],
            json={"blueprint_version_id": bp, "mode": "baseline"},
        )
        assert resp.status_code == 201, resp.text

    # 4th run → 402 plan_limit_exceeded.
    resp = await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={"blueprint_version_id": bp, "mode": "baseline"},
    )
    assert resp.status_code == 402
    body = resp.json()
    assert body["code"] == "plan_limit_exceeded"
    assert body["metric"] == "runs"
    assert body["tier"] == "free"


async def test_pro_workspace_allows_more_runs(client: AsyncClient) -> None:
    account = await _register(client, "usage4@b.co")
    await _set_plan_tier(client, account["workspace_id"], "pro")
    bp = await _create_blueprint(client, account["headers"])

    for _ in range(5):
        resp = await client.post(
            "/api/v1/simulations",
            headers=account["headers"],
            json={"blueprint_version_id": bp, "mode": "baseline"},
        )
        assert resp.status_code == 201, resp.text

    usage = (await client.get(
        "/api/v1/billing/usage", headers=account["headers"]
    )).json()
    assert usage["usage"]["runs_used"] == 5


async def test_monte_carlo_batch_consumes_mc_ticks(client: AsyncClient) -> None:
    account = await _register(client, "usage5@b.co")
    await _set_plan_tier(client, account["workspace_id"], "free")
    bp = await _create_blueprint(client, account["headers"])

    resp = await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={"blueprint_version_id": bp, "mode": "monte_carlo", "config": {"n_runs": 10}},
    )
    assert resp.status_code == 201, resp.text

    usage = (await client.get(
        "/api/v1/billing/usage", headers=account["headers"]
    )).json()
    assert usage["usage"]["mc_ticks_used"] == 10


async def test_metered_llm_tokens_from_stress_run(client: AsyncClient) -> None:
    account = await _register(client, "usage6@b.co")
    await _set_plan_tier(client, account["workspace_id"], "pro")
    bp = await _create_blueprint(client, account["headers"])

    resp = await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={"blueprint_version_id": bp, "mode": "stress"},
    )
    assert resp.status_code == 201, resp.text

    usage = (await client.get(
        "/api/v1/billing/usage", headers=account["headers"]
    )).json()
    assert usage["usage"]["llm_tokens_used"] > 0
