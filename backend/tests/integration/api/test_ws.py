"""Integration tests for the simulation WebSocket (T28)."""

import asyncio
import json
from pathlib import Path

import fakeredis.aioredis
import pytest
from app.main import create_app
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from starlette.websockets import WebSocketDisconnect

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _register(client: AsyncClient, email: str, name: str) -> tuple[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": name, "password": "password123"},
    )
    token = (
        await client.post(
            "/api/v1/auth/login", json={"email": email, "password": "password123"}
        )
    ).json()["access_token"]
    resp = await client.get(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
    )
    return token, resp.json()[0]["id"]


async def _make_run(headers: dict, client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/v1/blueprints",
        json={
            "name": "WS BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
        headers=headers,
    )
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=headers)
    version_id = versions.json()[0]["id"]
    run = await client.post(
        "/api/v1/simulations",
        json={"blueprint_version_id": version_id, "mode": "stress", "seed": 5},
        headers=headers,
    )
    return run.json()


def _setup(monkeypatch) -> tuple[TestClient, dict]:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    async def _build() -> dict:
        app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            token, ws_id = await _register(client, "ws-owner@b.co", "WsOwner")
            headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws_id}
            run = await _make_run(headers, client)
            token2, _ = await _register(client, "ws-other@b.co", "WsOther")
            return {"app": app, "token": token, "token2": token2, "run": run}

    ctx = asyncio.run(_build())
    return TestClient(ctx["app"]), ctx


def test_ws_snapshot_then_replay(monkeypatch) -> None:
    tc, ctx = _setup(monkeypatch)
    with tc:
        url = f"/ws/simulations/{ctx['run']['id']}?token={ctx['token']}"
        with tc.websocket_connect(url) as ws:
            snapshot = json.loads(ws.receive_text())
            assert snapshot["type"] == "snapshot"
            assert snapshot["data"]["id"] == ctx["run"]["id"]

            # Replay exactly the ticks persisted so far (stress run stops at
            # the first hurdle, so current_month - 1 ticks exist).
            expected = max(0, ctx["run"]["current_month"] - 1)
            got = 0
            for _ in range(expected):
                msg = json.loads(ws.receive_text())
                assert msg["type"] == "tick"
                assert "cash_balance" in msg["data"]["kpis"]
                got += 1
            assert got == expected


def test_ws_invalid_token_4401(monkeypatch) -> None:
    tc, ctx = _setup(monkeypatch)
    with tc:
        url = f"/ws/simulations/{ctx['run']['id']}?token=bogus"
        with pytest.raises(WebSocketDisconnect) as excinfo, tc.websocket_connect(url):
            pass
        assert excinfo.value.code == 4401


def test_ws_cross_workspace_4403(monkeypatch) -> None:
    tc, ctx = _setup(monkeypatch)
    with tc:
        url = f"/ws/simulations/{ctx['run']['id']}?token={ctx['token2']}"
        with pytest.raises(WebSocketDisconnect) as excinfo, tc.websocket_connect(url):
            pass
        assert excinfo.value.code == 4403


def test_ws_unknown_run_4403(monkeypatch) -> None:
    tc, ctx = _setup(monkeypatch)
    with tc:
        url = f"/ws/simulations/run_does_not_exist?token={ctx['token']}"
        with pytest.raises(WebSocketDisconnect) as excinfo, tc.websocket_connect(url):
            pass
        assert excinfo.value.code == 4403
