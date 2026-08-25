"""Integration tests for the benchmark API (Day 21)."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient


async def _register_workspace(client: AsyncClient, email: str) -> dict[str, Any]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Bm", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    ws = await client.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Bm Workspace"},
    )
    return {
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws.json()["id"]},
        "workspace_id": ws.json()["id"],
    }


async def test_get_percentile_returns_result(client: AsyncClient) -> None:
    account = await _register_workspace(client, "bm1@b.co")
    resp = await client.get(
        "/api/v1/benchmarks/percentile?score=64",
        headers=account["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert 0 <= data["percentile"] <= 100
    assert "sample_size" in data


async def test_get_cohort_returns_none_when_insufficient(client: AsyncClient) -> None:
    account = await _register_workspace(client, "bm2@b.co")
    resp = await client.get(
        "/api/v1/benchmarks/cohort?industry=unknown",
        headers=account["headers"],
    )
    assert resp.status_code == 200
    assert resp.json() is None
