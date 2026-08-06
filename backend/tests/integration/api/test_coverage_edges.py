"""Targeted edge-path tests that raise API-layer coverage (T47).

Each test hits an error/edge branch in an endpoint module that the happy-path
suites don't exercise — 404/403/409/422s, share/revoke, compare, export.
"""

import json
from pathlib import Path

from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _register(client: AsyncClient, email: str) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Edge", "password": "password123"},
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
            "name": "Edge BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
    )
    assert resp.status_code == 201, resp.text
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=headers)
    return versions.json()[0]["id"]


async def test_reports_404_unknown_run(client: AsyncClient) -> None:
    account = await _register(client, "edge1@b.co")
    resp = await client.get(
        "/api/v1/reports/simulations/run_missing/report",
        headers=account["headers"],
    )
    assert resp.status_code == 404


async def test_report_share_revoke_and_compare_errors(client: AsyncClient) -> None:
    account = await _register(client, "edge2@b.co")
    # Export on unknown run → 404.
    resp = await client.post(
        "/api/v1/reports/simulations/run_missing/report/export",
        headers=account["headers"],
    )
    assert resp.status_code == 404

    # Share on unknown run → 404.
    resp = await client.post(
        "/api/v1/reports/simulations/run_missing/report/share",
        headers=account["headers"],
    )
    assert resp.status_code == 404

    # Revoke on unknown run → 404.
    resp = await client.delete(
        "/api/v1/reports/simulations/run_missing/report/share",
        headers=account["headers"],
    )
    assert resp.status_code == 404

    # Compare with a missing run → 404.
    resp = await client.get(
        "/api/v1/reports/compare?a=run_a&b=run_b",
        headers=account["headers"],
    )
    assert resp.status_code == 404


async def test_control_errors(client: AsyncClient) -> None:
    account = await _register(client, "edge3@b.co")
    bpv = await _create_blueprint_version(client, account["headers"])

    run = (await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={"blueprint_version_id": bpv, "mode": "baseline", "seed": 1},
    )).json()

    # Control a completed run → 409.
    resp = await client.post(
        f"/api/v1/simulations/{run['id']}/control",
        headers=account["headers"],
        json={"action": "pause"},
    )
    assert resp.status_code == 409

    # Unknown action → 422.
    resp = await client.post(
        f"/api/v1/simulations/{run['id']}/control",
        headers=account["headers"],
        json={"action": "nope"},
    )
    assert resp.status_code == 422

    # Decide on a non-awaiting run → 409.
    resp = await client.post(
        f"/api/v1/simulations/{run['id']}/decide",
        headers=account["headers"],
        json={"event_id": "evt_x", "option_id": "A"},
    )
    assert resp.status_code == 409

    # Unknown run id → 404.
    resp = await client.get(
        "/api/v1/simulations/run_missing",
        headers=account["headers"],
    )
    assert resp.status_code == 404


async def test_workspace_errors(client: AsyncClient) -> None:
    account = await _register(client, "edge4@b.co")
    ws_id = account["workspace_id"]

    # Delete a foreign workspace id → 403 (not a member).
    resp = await client.delete(
        "/api/v1/workspaces/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {account['token']}"},
    )
    assert resp.status_code == 403

    # Update a foreign workspace → 403.
    resp = await client.patch(
        "/api/v1/workspaces/00000000-0000-0000-0000-000000000000",
        headers=account["headers"],
        json={"name": "Nope"},
    )
    assert resp.status_code == 403

    # Member listing of a foreign workspace → 403.
    resp = await client.get(
        "/api/v1/workspaces/00000000-0000-0000-0000-000000000000/members",
        headers=account["headers"],
    )
    assert resp.status_code == 403

    # Create invite with a bad email → 422.
    resp = await client.post(
        f"/api/v1/workspaces/{ws_id}/invites",
        headers=account["headers"],
        json={"email": "not-an-email", "role": "member"},
    )
    assert resp.status_code == 422


async def test_blueprint_and_scenario_errors(client: AsyncClient) -> None:
    account = await _register(client, "edge5@b.co")

    # Blueprint detail unknown → 404.
    resp = await client.get(
        "/api/v1/blueprints/bp_missing", headers=account["headers"]
    )
    assert resp.status_code == 404

    # Validate unknown → 404.
    resp = await client.get(
        "/api/v1/blueprints/bp_missing/validate", headers=account["headers"]
    )
    assert resp.status_code == 404

    # Scenario publish with a foreign version → 404.
    resp = await client.post(
        "/api/v1/scenarios",
        headers=account["headers"],
        json={
            "title": "X",
            "description": "D",
            "category": "custom",
            "blueprint_version_id": "bpv_missing",
        },
    )
    assert resp.status_code == 404

    # Clone unknown scenario → 404.
    resp = await client.post(
        "/api/v1/scenarios/scn_missing/clone",
        headers=account["headers"],
    )
    assert resp.status_code == 404


async def test_api_keys_and_admin_errors(client: AsyncClient) -> None:
    account = await _register(client, "edge6@b.co")

    # Create a key, then revoke an unknown key id → 404.
    created = await client.post(
        "/api/v1/api-keys",
        headers=account["headers"],
        json={"name": "CI", "scopes": ["runs:read"]},
    )
    assert created.status_code == 201
    resp = await client.delete(
        "/api/v1/api-keys/key_missing", headers=account["headers"]
    )
    assert resp.status_code == 404

    # Admin stats as a non-admin → 403.
    resp = await client.get("/api/v1/admin/stats", headers=account["headers"])
    assert resp.status_code == 403
