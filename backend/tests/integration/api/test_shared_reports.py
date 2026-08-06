"""Integration tests for shareable report endpoints (T44)."""

import json
from pathlib import Path

from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _register(client: AsyncClient, email: str) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Share", "password": "password123"},
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


async def _create_completed_run(client: AsyncClient, account: dict) -> str:
    resp = await client.post(
        "/api/v1/blueprints",
        headers=account["headers"],
        json={
            "name": "Shared BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
    )
    assert resp.status_code == 201
    bp_id = resp.json()["id"]
    versions = await client.get(
        f"/api/v1/blueprints/{bp_id}/versions", headers=account["headers"]
    )
    version_id = versions.json()[0]["id"]

    start = await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={
            "blueprint_version_id": version_id,
            "mode": "monte_carlo",
            "seed": 42,
            "config": {"months": 24, "n_runs": 5},
        },
    )
    assert start.status_code == 201, start.text
    return start.json()["id"]


async def test_share_report_returns_token_and_public_get(client: AsyncClient) -> None:
    account = await _register(client, "share1@b.co")
    run_id = await _create_completed_run(client, account)

    # Generate the report (creates the persisted Format C).
    rep = await client.get(
        f"/api/v1/reports/simulations/{run_id}/report",
        headers=account["headers"],
    )
    assert rep.status_code == 200

    share = await client.post(
        f"/api/v1/reports/simulations/{run_id}/report/share",
        headers=account["headers"],
    )
    assert share.status_code == 201
    body = share.json()
    assert body["token"]
    assert "/shared/reports/" in body["share_url"]

    # Public GET without auth.
    pub = await client.get(f"/api/v1/reports/shared/{body['token']}")
    assert pub.status_code == 200
    pub_body = pub.json()
    assert pub_body["blueprint_name"] == "Shared BP"
    assert "SURVIVAL METRICS" in pub_body["content_md"]


async def test_unknown_token_404(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/reports/shared/does-not-exist")
    assert resp.status_code == 404


async def test_revoke_invalidates_token(client: AsyncClient) -> None:
    account = await _register(client, "share2@b.co")
    run_id = await _create_completed_run(client, account)
    await client.get(
        f"/api/v1/reports/simulations/{run_id}/report",
        headers=account["headers"],
    )
    share = await client.post(
        f"/api/v1/reports/simulations/{run_id}/report/share",
        headers=account["headers"],
    )
    token = share.json()["token"]

    # Public GET works before revoke.
    assert (await client.get(f"/api/v1/reports/shared/{token}")).status_code == 200

    revoke = await client.delete(
        f"/api/v1/reports/simulations/{run_id}/report/share",
        headers=account["headers"],
    )
    assert revoke.status_code == 204

    # Public GET now 404s.
    assert (await client.get(f"/api/v1/reports/shared/{token}")).status_code == 404

    # Authenticated report endpoint still works.
    auth = await client.get(
        f"/api/v1/reports/simulations/{run_id}/report",
        headers=account["headers"],
    )
    assert auth.status_code == 200
