"""Integration tests for the deep-dive report endpoints (Day 06)."""

from __future__ import annotations

from httpx import AsyncClient


async def _register_workspace(client: AsyncClient, email: str) -> tuple[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Deep", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    ws = await client.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Deep Workspace"},
    )
    return token, ws.json()["id"]


async def test_enqueue_deep_report_returns_queued(client: AsyncClient) -> None:
    token, ws_id = await _register_workspace(client, "deep1@b.co")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws_id}

    resp = await client.post(
        "/api/v1/reports/deep-dive",
        headers=headers,
        json={"run_id": "run_missing", "report_type": "resilience_audit"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["job_id"].startswith("dr_")
    assert body["status"] == "queued"
    assert body["tier"] == "free"  # fresh workspace defaults to free plan
    assert body["total_sections"] == 3


async def test_enqueue_deep_report_unknown_type_returns_400(client: AsyncClient) -> None:
    token, ws_id = await _register_workspace(client, "deep2@b.co")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws_id}

    resp = await client.post(
        "/api/v1/reports/deep-dive",
        headers=headers,
        json={"run_id": "run_missing", "report_type": "nonexistent"},
    )
    assert resp.status_code == 400
    assert "Unknown report type" in resp.json()["detail"]


async def test_status_unknown_job_returns_404(client: AsyncClient) -> None:
    token, ws_id = await _register_workspace(client, "deep3@b.co")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws_id}

    resp = await client.get(
        "/api/v1/reports/deep-dive/dr_unknown/status", headers=headers
    )
    assert resp.status_code == 404


async def test_download_unknown_job_returns_404(client: AsyncClient) -> None:
    token, ws_id = await _register_workspace(client, "deep4@b.co")
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws_id}

    resp = await client.get(
        "/api/v1/reports/deep-dive/dr_unknown/download", headers=headers
    )
    assert resp.status_code == 404
