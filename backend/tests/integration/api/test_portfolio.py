"""Integration tests for the portfolio endpoints (Day 20)."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient


async def _register_workspace(client: AsyncClient, email: str) -> dict[str, Any]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Pf", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    ws = await client.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Pf Workspace"},
    )
    return {
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws.json()["id"]},
        "workspace_id": ws.json()["id"],
    }


async def test_create_portfolio_and_summary(client: AsyncClient) -> None:
    account = await _register_workspace(client, "pf1@b.co")
    headers = account["headers"]

    resp = await client.post("/api/v1/portfolios/", headers=headers, json={"name": "My Fund"})
    assert resp.status_code == 201
    portfolio_id = resp.json()["portfolio_id"]
    assert portfolio_id.startswith("pf_")

    summary = await client.get(f"/api/v1/portfolios/{portfolio_id}/summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["name"] == "My Fund"
    assert body["member_count"] == 0


async def test_add_and_remove_workspace(client: AsyncClient) -> None:
    account = await _register_workspace(client, "pf2@b.co")
    headers = account["headers"]
    ws_id = account["workspace_id"]

    resp = await client.post("/api/v1/portfolios/", headers=headers, json={"name": "Fund B"})
    portfolio_id = resp.json()["portfolio_id"]

    added = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/workspaces",
        headers=headers,
        params={"workspace_id": ws_id, "label": "Portfolio Co"},
    )
    assert added.status_code == 201

    summary = await client.get(f"/api/v1/portfolios/{portfolio_id}/summary", headers=headers)
    body = summary.json()
    assert body["member_count"] == 1
    assert body["workspaces"][0]["label"] == "Portfolio Co"

    removed = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/workspaces/{ws_id}", headers=headers
    )
    assert removed.status_code == 200
    summary2 = await client.get(f"/api/v1/portfolios/{portfolio_id}/summary", headers=headers)
    assert summary2.json()["member_count"] == 0


async def test_summary_unknown_portfolio_404(client: AsyncClient) -> None:
    account = await _register_workspace(client, "pf3@b.co")
    resp = await client.get(
        "/api/v1/portfolios/pf_unknown/summary", headers=account["headers"]
    )
    assert resp.status_code == 404
