"""Integration tests for the portfolio endpoints (Day 26)."""

from __future__ import annotations

import uuid
from typing import Any

from app.db.session import async_session_factory
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str) -> dict[str, Any]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Pf", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    ws = await client.post(
        "/api/v1/workspaces", headers=auth_headers, json={"name": "Pf Workspace"}
    )
    return {
        "auth_headers": auth_headers,
        "workspace_id": ws.json()["id"],
    }


async def _make_workspace(
    client: AsyncClient, auth_headers: dict[str, str], name: str
) -> str:
    ws = await client.post("/api/v1/workspaces", headers=auth_headers, json={"name": name})
    return ws.json()["id"]


async def _add_run(ws_id: str, score: float) -> None:
    from app.models.blueprint import Blueprint, BlueprintVersion
    from app.models.simulation import RunStatus, SimulationRun

    async with async_session_factory() as session:
        bp = Blueprint(name="B", industry="tech", stage="seed", workspace_id=uuid.UUID(ws_id))
        session.add(bp)
        await session.flush()
        bpv = BlueprintVersion(
            blueprint_id=bp.id, version=1, payload={"x": 1}, vulnerabilities=[]
        )
        session.add(bpv)
        await session.flush()
        session.add(
            SimulationRun(
                workspace_id=uuid.UUID(ws_id),
                blueprint_version_id=bpv.id,
                mode="monte_carlo",
                status=RunStatus.COMPLETED,
                seed=1,
                config={},
                result={"survival_rate": 0.7, "resilience_score": score},
            )
        )
        await session.commit()


async def test_create_portfolio_returns_201(client: AsyncClient) -> None:
    account = await _register(client, "pf1@b.co")
    resp = await client.post(
        "/api/v1/portfolios/", headers=account["auth_headers"], json={"name": "My Fund"}
    )
    assert resp.status_code == 201
    portfolio_id = resp.json()["portfolio_id"]
    assert portfolio_id.startswith("pf_")


async def test_add_workspace_to_portfolio(client: AsyncClient) -> None:
    account = await _register(client, "pf2@b.co")
    created = await client.post(
        "/api/v1/portfolios/", headers=account["auth_headers"], json={"name": "Fund B"}
    )
    portfolio_id = created.json()["portfolio_id"]

    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/workspaces",
        headers=account["auth_headers"],
        params={"workspace_id": account["workspace_id"], "label": "Portfolio Co"},
    )
    assert resp.status_code == 201


async def test_get_portfolio_summary(client: AsyncClient) -> None:
    account = await _register(client, "pf3@b.co")
    ws_low = await _make_workspace(client, account["auth_headers"], "Low Co")
    ws_high = await _make_workspace(client, account["auth_headers"], "High Co")
    await _add_run(ws_low, 40)
    await _add_run(ws_high, 88)

    created = await client.post(
        "/api/v1/portfolios/", headers=account["auth_headers"], json={"name": "Fund C"}
    )
    portfolio_id = created.json()["portfolio_id"]
    for ws_id, label in ((ws_low, "Low Co"), (ws_high, "High Co")):
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/workspaces",
            headers=account["auth_headers"],
            params={"workspace_id": ws_id, "label": label},
        )

    resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/summary", headers=account["auth_headers"]
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["member_count"] == 2
    assert body["workspaces"][0]["workspace_id"] == ws_high
    assert body["workspaces"][0]["resilience_score"] == 88.0
    assert body["workspaces"][1]["workspace_id"] == ws_low


async def test_portfolio_not_found_returns_404(client: AsyncClient) -> None:
    account = await _register(client, "pf4@b.co")
    resp = await client.get(
        "/api/v1/portfolios/pf_unknown/summary", headers=account["auth_headers"]
    )
    assert resp.status_code == 404
