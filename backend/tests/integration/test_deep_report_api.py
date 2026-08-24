"""Day 06 — Deep-Dive report API integration tests.

Covers enqueueing a report job, status polling, PDF download guards, auth,
tier-derived section counts, and request validation. The Celery enqueue stub
keeps POSTs fast and side-effect free; the status endpoint's Redis dependency
is pointed at fakeredis so the progress key is controllable.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import fakeredis.aioredis
from app.api.v1.endpoints import deep_report as deep_report_module
from app.db.session import async_session_factory
from app.models.workspace import Workspace
from httpx import AsyncClient

REPORT_URL = "/api/v1/reports/deep-dive"


class _TaskStub:
    """Stands in for the Celery task so POSTs don't run the heavy report."""

    def __init__(self) -> None:
        self.enqueued: list[dict[str, Any]] = []

    def delay(self, **kwargs: Any) -> None:
        self.enqueued.append(kwargs)


def _stub_task(monkeypatch) -> _TaskStub:
    stub = _TaskStub()
    monkeypatch.setattr(deep_report_module, "generate_deep_report", stub)
    return stub


class _FailingTask:
    """Stands in for the Celery task when the broker is unreachable."""

    def delay(self, **_kwargs: Any) -> None:
        raise RuntimeError("broker unavailable")


async def _fake_redis(monkeypatch) -> fakeredis.aioredis.FakeRedis:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)
    monkeypatch.setattr(deep_report_module, "get_redis", lambda: fake)
    return fake


async def _workspace(client: AsyncClient, email: str, tier: str = "free") -> dict[str, Any]:
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
    ws_id = ws.json()["id"]
    if tier != "free":
        async with async_session_factory() as session:
            workspace = await session.get(Workspace, uuid.UUID(ws_id))
            assert workspace is not None
            workspace.plan_tier = tier
            await session.commit()
    return {
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws_id},
        "workspace_id": ws_id,
    }


async def test_request_deep_report_queued(client: AsyncClient, monkeypatch) -> None:
    _stub_task(monkeypatch)
    acc = await _workspace(client, "day06-a@b.co", "free")

    resp = await client.post(
        REPORT_URL,
        headers=acc["headers"],
        json={"run_id": "run_missing", "report_type": "resilience_audit"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["job_id"].startswith("dr_")
    assert body["status"] == "queued"


async def test_get_report_status_404_for_unknown_job(client: AsyncClient) -> None:
    acc = await _workspace(client, "day06-b@b.co")

    resp = await client.get(f"{REPORT_URL}/dr_nonexistent/status", headers=acc["headers"])
    assert resp.status_code == 404


async def test_download_404_before_completion(client: AsyncClient) -> None:
    acc = await _workspace(client, "day06-c@b.co")

    resp = await client.get(f"{REPORT_URL}/dr_nonexistent/download", headers=acc["headers"])
    assert resp.status_code == 404


async def test_report_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(REPORT_URL, json={"run_id": "run_missing"})
    assert resp.status_code == 401


async def test_free_tier_gets_3_sections(client: AsyncClient, monkeypatch) -> None:
    _stub_task(monkeypatch)
    acc = await _workspace(client, "day06-e@b.co", "free")

    resp = await client.post(REPORT_URL, headers=acc["headers"], json={"run_id": "run_missing"})
    assert resp.status_code == 202
    body = resp.json()
    assert body["tier"] == "free"
    assert body["total_sections"] == 3


async def test_pro_tier_gets_13_sections(client: AsyncClient, monkeypatch) -> None:
    _stub_task(monkeypatch)
    acc = await _workspace(client, "day06-f@b.co", "pro")

    resp = await client.post(REPORT_URL, headers=acc["headers"], json={"run_id": "run_missing"})
    assert resp.status_code == 202
    body = resp.json()
    assert body["tier"] == "pro"
    assert body["total_sections"] == 13


async def test_job_status_in_progress_after_enqueue(
    client: AsyncClient, monkeypatch
) -> None:
    _stub_task(monkeypatch)
    fake = await _fake_redis(monkeypatch)
    acc = await _workspace(client, "day06-g@b.co", "free")

    resp = await client.post(REPORT_URL, headers=acc["headers"], json={"run_id": "run_missing"})
    job_id = resp.json()["job_id"]

    # Simulate the worker's partial progress, then poll the status endpoint.
    await fake.set(
        f"deep_report:progress:{job_id}",
        json.dumps(
            {
                "job_id": job_id,
                "run_id": "run_missing",
                "tier": "free",
                "section": 1,
                "total": 3,
                "status": "done",
            }
        ),
    )

    status = await client.get(f"{REPORT_URL}/{job_id}/status", headers=acc["headers"])
    assert status.status_code == 200
    assert status.json()["status"] in {"queued", "in_progress"}


async def test_invalid_report_type_returns_422(client: AsyncClient) -> None:
    acc = await _workspace(client, "day06-h@b.co", "free")

    resp = await client.post(
        REPORT_URL,
        headers=acc["headers"],
        json={"run_id": "run_missing", "report_type": "nonexistent"},
    )
    assert resp.status_code == 422


async def test_enqueue_failure_persists_failed_and_status_returns_failed(
    client: AsyncClient, monkeypatch
) -> None:
    """Broker-down enqueue returns FAILED and status reports FAILED (not 404)."""
    monkeypatch.setattr(deep_report_module, "generate_deep_report", _FailingTask())
    fake = await _fake_redis(monkeypatch)
    acc = await _workspace(client, "day06-i@b.co", "free")

    resp = await client.post(
        REPORT_URL,
        headers=acc["headers"],
        json={"run_id": "run_missing", "report_type": "resilience_audit"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "failed"
    assert await fake.exists(f"deep_report:progress:{body['job_id']}")

    status = await client.get(
        f"{REPORT_URL}/{body['job_id']}/status", headers=acc["headers"]
    )
    assert status.status_code == 200
    assert status.json()["status"] == "failed"


async def test_status_returns_failed_for_error_progress(
    client: AsyncClient, monkeypatch
) -> None:
    """A stored 'error' progress record maps to FAILED status."""
    _stub_task(monkeypatch)
    fake = await _fake_redis(monkeypatch)
    acc = await _workspace(client, "day06-j@b.co", "free")

    resp = await client.post(REPORT_URL, headers=acc["headers"], json={"run_id": "run_missing"})
    job_id = resp.json()["job_id"]

    await fake.set(
        f"deep_report:progress:{job_id}",
        json.dumps(
            {
                "job_id": job_id,
                "run_id": "run_missing",
                "tier": "free",
                "section": 2,
                "total": 3,
                "status": "error",
            }
        ),
        ex=3600,
    )

    status = await client.get(f"{REPORT_URL}/{job_id}/status", headers=acc["headers"])
    assert status.status_code == 200
    assert status.json()["status"] == "failed"
    assert status.json()["pdf_url"] is None
