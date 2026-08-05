"""Integration tests for POST /api/v1/blueprints/{id}/review (T22)."""

import json
from pathlib import Path

from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _register(client: AsyncClient, email: str, name: str):
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": name, "password": "password123"},
    )
    return (await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )).json()["access_token"]


async def _owner(client: AsyncClient):
    token = await _register(client, "review-owner@b.co", "ReviewOwner")
    resp = await client.get(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
    )
    ws = resp.json()[0]
    return {
        "token": token,
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws["id"]},
    }


async def _outsider(client: AsyncClient):
    token = await _register(client, "review-out@b.co", "ReviewOut")
    resp = await client.get(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
    )
    ws = resp.json()[0]
    return {"headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws["id"]}}


async def _create_blueprint(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/blueprints",
        json={
            "name": "Review Me",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_review_returns_schema_and_persists(client: AsyncClient, monkeypatch) -> None:
    owner = await _owner(client)
    bp_id = await _create_blueprint(client, owner["headers"])

    # Deterministic mock review (no API key in test env).
    from app.agents.llm.base import MockProvider

    canned = json.dumps(
        {
            "overall_assessment": "Solid but concentrated.",
            "identified_vulnerabilities": [
                {
                    "type": "liquidity",
                    "severity": "high",
                    "description": "Tight runway.",
                    "mitigation_suggestion": "Cut burn.",
                }
            ],
        }
    )

    def _mock_provider(settings):
        p = MockProvider(model=settings.llm_model)
        p.register("BLUEPRINT", canned)
        return p

    monkeypatch.setattr("app.agents.llm.factory.get_llm_provider", _mock_provider)

    resp = await client.post(
        f"/api/v1/blueprints/{bp_id}/review", headers=owner["headers"]
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_assessment"]
    assert body["reviewed_version"] == 1
    assert body["llm_model"]
    assert len(body["identified_vulnerabilities"]) == 1
    assert body["identified_vulnerabilities"][0]["type"] == "liquidity"

    # Persisted on the current version.
    detail = await client.get(f"/api/v1/blueprints/{bp_id}", headers=owner["headers"])
    assert detail.status_code == 200
    assert detail.json()["vulnerabilities"][0]["severity"] == "high"


async def test_review_404_unknown_blueprint(client: AsyncClient) -> None:
    owner = await _owner(client)
    resp = await client.post("/api/v1/blueprints/nope/review", headers=owner["headers"])
    assert resp.status_code == 404


async def test_review_403_cross_workspace(client: AsyncClient) -> None:
    owner = await _owner(client)
    outsider = await _outsider(client)
    bp_id = await _create_blueprint(client, owner["headers"])

    resp = await client.post(
        f"/api/v1/blueprints/{bp_id}/review", headers=outsider["headers"]
    )
    assert resp.status_code == 404  # cross-workspace blueprints read as 404


async def test_review_502_when_llm_always_invalid(client: AsyncClient, monkeypatch) -> None:
    owner = await _owner(client)
    bp_id = await _create_blueprint(client, owner["headers"])

    def _bad_provider(settings):
        from app.agents.llm.base import MockProvider

        p = MockProvider(model=settings.llm_model)
        p.register("BLUEPRINT", "not json at all")
        return p

    monkeypatch.setattr("app.agents.llm.factory.get_llm_provider", _bad_provider)

    resp = await client.post(
        f"/api/v1/blueprints/{bp_id}/review", headers=owner["headers"]
    )
    assert resp.status_code == 502
