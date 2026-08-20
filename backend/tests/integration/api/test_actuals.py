"""Integration tests for the actuals endpoints (Day 15)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
_VALID_PAYLOAD = json.loads((FIXTURES / "blueprint_golden.json").read_text())


async def _register_workspace(client: AsyncClient, email: str) -> dict[str, Any]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Act", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    ws = await client.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Act Workspace"},
    )
    return {
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws.json()["id"]},
        "workspace_id": ws.json()["id"],
    }


async def _create_blueprint(client: AsyncClient, headers: dict[str, str]) -> str:
    resp = await client.post(
        "/api/v1/blueprints",
        headers=headers,
        json={
            "name": "Act BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _VALID_PAYLOAD,
        },
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


async def test_upload_actuals_and_history(client: AsyncClient) -> None:
    account = await _register_workspace(client, "act1@b.co")
    bp_id = await _create_blueprint(client, account["headers"])

    resp = await client.post(
        "/api/v1/actuals/upload",
        headers=account["headers"],
        json={
            "blueprint_id": bp_id,
            "csv_content": "month,revenue,costs\n1,12000,14000\n2,15000,14200",
            "column_mapping": {},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["records_created"] == 2
    assert body["records_updated"] == 0

    history = await client.get(
        f"/api/v1/actuals/{bp_id}/history", headers=account["headers"]
    )
    assert history.status_code == 200
    rows = history.json()
    assert len(rows) == 2
    assert rows[0]["month"] == 1
    assert rows[0]["revenue"] == 12000.0


async def test_upload_actuals_validation_warning(client: AsyncClient) -> None:
    account = await _register_workspace(client, "act2@b.co")
    bp_id = await _create_blueprint(client, account["headers"])

    resp = await client.post(
        "/api/v1/actuals/upload",
        headers=account["headers"],
        json={
            "blueprint_id": bp_id,
            "csv_content": "month,revenue\n1,12000\nbad,15000",
            "column_mapping": {},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["records_created"] == 1
    assert len(body["validation_warnings"]) == 1


async def test_variance_requires_actuals(client: AsyncClient) -> None:
    account = await _register_workspace(client, "act3@b.co")
    bp_id = await _create_blueprint(client, account["headers"])

    resp = await client.get(
        f"/api/v1/actuals/{bp_id}/variance", headers=account["headers"]
    )
    assert resp.status_code == 404  # no actuals imported yet
