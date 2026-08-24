"""Integration tests for the advisory board API (Day 17).

Covers the request/poll contract: POST queues a board review (202 + ``adv_``
job id) and returns its result, and an unknown job yields a 404. The Celery +
LLM layers are bypassed: the in-process background task runs against the mock
LLM provider and fakeredis, so the job reaches a terminal state immediately.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fakeredis.aioredis
import pytest
from app.api.v1.endpoints import advisory as advisory_module
from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
_VALID_PAYLOAD = json.loads((FIXTURES / "blueprint_golden.json").read_text())


@pytest.fixture(autouse=True)
def _fake_redis(monkeypatch: Any) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(advisory_module, "get_redis", lambda: fake)


async def _workspace_and_blueprint(client: AsyncClient, email: str) -> dict[str, Any]:
    """Register a user, create a workspace, and create a valid blueprint."""
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
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-Id": ws.json()["id"],
    }
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
    return {"headers": headers, "blueprint_id": bp.json()["id"]}


async def test_request_board_review_returns_202(client: AsyncClient) -> None:
    ctx = await _workspace_and_blueprint(client, "day17-a@b.co")

    resp = await client.post(
        f"/api/v1/advisory/blueprints/{ctx['blueprint_id']}/board-review",
        headers=ctx["headers"],
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    assert job_id.startswith("adv_")

    # GET should return the completed result: 4 reviews and a summary.
    final = await client.get(
        f"/api/v1/advisory/board-review/{job_id}", headers=ctx["headers"]
    )
    assert final.status_code == 200
    body = final.json()
    assert body["status"] == "complete"
    result = body["result"]
    assert len(result["reviews"]) == 4
    assert "consensus_verdict" in result["summary"]


async def test_get_board_review_404_for_unknown(client: AsyncClient) -> None:
    ctx = await _workspace_and_blueprint(client, "day17-b@b.co")

    resp = await client.get(
        "/api/v1/advisory/board-review/adv_missing", headers=ctx["headers"]
    )
    assert resp.status_code == 404
