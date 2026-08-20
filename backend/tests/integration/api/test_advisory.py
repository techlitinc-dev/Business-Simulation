"""Integration tests for the advisory board endpoints (Day 16)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fakeredis.aioredis
import pytest
from app.api.v1.endpoints import advisory as advisory_module
from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
_VALID_PAYLOAD = json.loads((FIXTURES / "blueprint_golden.json").read_text())


@pytest.fixture(autouse=True)
def _fake_redis(monkeypatch: Any) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(advisory_module, "get_redis", lambda: fake)


async def _register_workspace(client: AsyncClient, email: str) -> dict[str, Any]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Adv", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    ws = await client.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Adv Workspace"},
    )
    return {
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws.json()["id"]},
        "workspace_id": ws.json()["id"],
    }


async def test_board_review_queues_and_completes(client: AsyncClient) -> None:
    account = await _register_workspace(client, "adv1@b.co")
    headers = account["headers"]

    bp = await client.post(
        "/api/v1/blueprints",
        headers=headers,
        json={
            "name": "Adv BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _VALID_PAYLOAD,
        },
    )
    bp_id = bp.json()["id"]

    resp = await client.post(
        f"/api/v1/advisory/blueprints/{bp_id}/board-review", headers=headers
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    assert job_id.startswith("adv_")

    # The background task runs in-process under the test client; the mock
    # provider + fakeredis mean the job should reach a terminal state quickly.
    final = await client.get(f"/api/v1/advisory/board-review/{job_id}", headers=headers)
    assert final.status_code == 200
    body = final.json()
    assert body["status"] in ("complete", "running")
    if body["status"] == "complete":
        assert len(body["result"]["reviews"]) == 4


async def test_board_review_unknown_job_404(client: AsyncClient) -> None:
    account = await _register_workspace(client, "adv2@b.co")
    resp = await client.get(
        "/api/v1/advisory/board-review/adv_nope", headers=account["headers"]
    )
    assert resp.status_code == 404
