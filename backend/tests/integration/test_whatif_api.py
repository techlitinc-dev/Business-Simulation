"""Integration tests for the What-If Lab API endpoints (Day 10)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from app.db.session import async_session_factory
from app.models.workspace import Workspace
from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
_VALID_PAYLOAD = json.loads((FIXTURES / "blueprint_golden.json").read_text())

CHURN_PARAM = "revenue_engine.streams.0.churn_monthly"


async def _register(client: AsyncClient, email: str, name: str) -> dict[str, Any]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": name, "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    ws = await client.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": f"{name} Workspace"},
    )
    return {
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws.json()["id"]},
        "workspace_id": ws.json()["id"],
    }


async def _set_plan_tier(ws_id: str, tier: str) -> None:
    async with async_session_factory() as session:
        workspace = await session.get(Workspace, uuid.UUID(ws_id))
        assert workspace is not None
        workspace.plan_tier = tier
        await session.commit()


async def _create_blueprint(client: AsyncClient, headers: dict[str, str]) -> str:
    resp = await client.post(
        "/api/v1/blueprints",
        headers=headers,
        json={
            "name": "WhatIf API BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _VALID_PAYLOAD,
        },
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


async def _pro_account(client: AsyncClient, email: str) -> dict[str, Any]:
    account = await _register(client, email, "WhatIfPro")
    await _set_plan_tier(account["workspace_id"], "pro")
    return account


def _sweep_body(
    workspace_id: str, blueprint_id: str, **overrides: Any
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "workspace_id": workspace_id,
        "blueprint_id": blueprint_id,
        "param": CHURN_PARAM,
        "min_value": 0.02,
        "max_value": 0.12,
        "steps": 3,
        "mc_runs": 5,
    }
    body.update(overrides)
    return body


async def test_sweep_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/whatif/sweep",
        json=_sweep_body(
            "00000000-0000-0000-0000-000000000000", "bp_001", steps=3
        ),
    )
    assert resp.status_code == 401


async def test_sweep_returns_result(client: AsyncClient) -> None:
    account = await _pro_account(client, "whatifapi1@b.co")
    bp_id = await _create_blueprint(client, account["headers"])

    resp = await client.post(
        "/api/v1/whatif/sweep",
        headers=account["headers"],
        json=_sweep_body(account["workspace_id"], bp_id, steps=3),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["grid"]) == 3
    assert body["grid"][0]["param_value"] < body["grid"][-1]["param_value"]


async def test_save_version_creates_new_version(client: AsyncClient) -> None:
    account = await _pro_account(client, "whatifapi2@b.co")
    bp_id = await _create_blueprint(client, account["headers"])

    resp = await client.post(
        "/api/v1/whatif/save-version",
        headers=account["headers"],
        json={
            "blueprint_id": bp_id,
            "param": CHURN_PARAM,
            "value": 0.04,
            "version_label": "Optimistic Churn",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["id"].startswith("bpv_")
    assert body["version"] == 2  # current_version was 1
    assert body["payload"]["revenue_engine"]["streams"][0]["churn_monthly"] == 0.04


async def test_free_plan_sweep_returns_402(client: AsyncClient) -> None:
    account = await _register(client, "whatifapi3@b.co", "WhatIfFree")
    # Plan tier stays "free".

    resp = await client.post(
        "/api/v1/whatif/sweep",
        headers=account["headers"],
        json=_sweep_body(account["workspace_id"], "bp_x"),
    )
    assert resp.status_code == 402
    assert "Pro plan required" in resp.json()["detail"]


async def test_breakeven_returns_result(client: AsyncClient) -> None:
    account = await _pro_account(client, "whatifapi4@b.co")
    bp_id = await _create_blueprint(client, account["headers"])

    resp = await client.post(
        "/api/v1/whatif/breakeven",
        headers=account["headers"],
        json={
            "workspace_id": account["workspace_id"],
            "blueprint_id": bp_id,
            "param": CHURN_PARAM,
            "search_min": 0.02,
            "search_max": 0.15,
            "target_survival": 0.5,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "breakeven_value" in body
    assert 0.02 <= body["breakeven_value"] <= 0.15


async def test_sweep_invalid_steps(client: AsyncClient) -> None:
    account = await _pro_account(client, "whatifapi5@b.co")
    bp_id = await _create_blueprint(client, account["headers"])

    resp = await client.post(
        "/api/v1/whatif/sweep",
        headers=account["headers"],
        json=_sweep_body(account["workspace_id"], bp_id, steps=1),
    )
    assert resp.status_code == 422


async def test_save_version_unknown_blueprint(client: AsyncClient) -> None:
    account = await _pro_account(client, "whatifapi6@b.co")

    resp = await client.post(
        "/api/v1/whatif/save-version",
        headers=account["headers"],
        json={
            "blueprint_id": "bp_does_not_exist",
            "param": CHURN_PARAM,
            "value": 0.04,
        },
    )
    assert resp.status_code == 404
