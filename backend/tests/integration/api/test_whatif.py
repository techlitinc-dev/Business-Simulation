"""Integration tests for the What-If Lab endpoints (Day 10)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from app.db.session import async_session_factory
from app.models.workspace import Workspace
from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
_VALID_PAYLOAD = json.loads((FIXTURES / "blueprint_golden.json").read_text())


async def _register(client: AsyncClient, email: str) -> dict[str, Any]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "WhatIf", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    ws = await client.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "WhatIf Workspace"},
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
            "name": "WhatIf BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _VALID_PAYLOAD,
        },
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


async def test_sweep_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/whatif/sweep",
        json={
            "workspace_id": "00000000-0000-0000-0000-000000000000",
            "blueprint_id": "bp_001",
            "param": "monthly_churn",
            "min_value": 0.02,
            "max_value": 0.12,
            "steps": 3,
        },
    )
    assert resp.status_code == 401


async def test_sweep_requires_pro(client: AsyncClient) -> None:
    account = await _register(client, "whatif1@b.co")
    resp = await client.post(
        "/api/v1/whatif/sweep",
        headers=account["headers"],
        json={
            "workspace_id": account["workspace_id"],
            "blueprint_id": "bp_x",
            "param": "revenue_engine.streams.0.churn_monthly",
            "min_value": 0.02,
            "max_value": 0.12,
            "steps": 5,
            "mc_runs": 5,
        },
    )
    assert resp.status_code == 402


async def test_sweep_returns_grid_for_pro(client: AsyncClient) -> None:
    account = await _register(client, "whatif2@b.co")
    await _set_plan_tier(account["workspace_id"], "pro")
    bp_id = await _create_blueprint(client, account["headers"])

    resp = await client.post(
        "/api/v1/whatif/sweep",
        headers=account["headers"],
        json={
            "workspace_id": account["workspace_id"],
            "blueprint_id": bp_id,
            "param": "revenue_engine.streams.0.churn_monthly",
            "min_value": 0.02,
            "max_value": 0.12,
            "steps": 5,
            "mc_runs": 5,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["grid"]) == 5
    assert body["grid"][0]["param_value"] < body["grid"][-1]["param_value"]


async def test_breakeven_returns_result_for_pro(client: AsyncClient) -> None:
    account = await _register(client, "whatif3@b.co")
    await _set_plan_tier(account["workspace_id"], "pro")
    bp_id = await _create_blueprint(client, account["headers"])

    resp = await client.post(
        "/api/v1/whatif/breakeven",
        headers=account["headers"],
        json={
            "workspace_id": account["workspace_id"],
            "blueprint_id": bp_id,
            "param": "revenue_engine.streams.0.churn_monthly",
            "search_min": 0.02,
            "search_max": 0.2,
            "target_survival": 0.5,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "breakeven_value" in body
    assert "monthly_churn" in body["message"] or "churn" in body["message"]


async def test_save_version_forks_blueprint(client: AsyncClient) -> None:
    account = await _register(client, "whatif4@b.co")
    await _set_plan_tier(account["workspace_id"], "pro")
    bp_id = await _create_blueprint(client, account["headers"])

    resp = await client.post(
        "/api/v1/whatif/save-version",
        headers=account["headers"],
        json={
            "blueprint_id": bp_id,
            "param": "revenue_engine.streams.0.churn_monthly",
            "value": 0.09,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["id"].startswith("bpv_")
    assert body["version"] == 2  # current_version was 1
    # The BlueprintVersion model has no label column yet, so the label from
    # SaveVersionRequest is accepted but not echoed back.
    assert "label" not in body

    # Verify the override landed in the new version's payload.
    versions = await client.get(
        f"/api/v1/blueprints/{bp_id}/versions", headers=account["headers"]
    )
    latest = versions.json()[0]
    assert latest["version"] == 2
    assert latest["payload"]["revenue_engine"]["streams"][0]["churn_monthly"] == 0.09
