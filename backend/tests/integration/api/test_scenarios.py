"""Integration tests for scenario marketplace endpoints (T42)."""

import json
from pathlib import Path

from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _register(client: AsyncClient, email: str) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Scen", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    ws = (await client.get(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
    )).json()[0]
    return {
        "token": token,
        "workspace_id": ws["id"],
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws["id"]},
    }


async def _create_blueprint_version(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/blueprints",
        headers=headers,
        json={
            "name": "Scenario Source",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
    )
    assert resp.status_code == 201, resp.text
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=headers)
    return versions.json()[0]["id"]


async def test_publish_returns_201_with_payload(client: AsyncClient) -> None:
    account = await _register(client, "scen1@b.co")
    version_id = await _create_blueprint_version(client, account["headers"])

    resp = await client.post(
        "/api/v1/scenarios",
        headers=account["headers"],
        json={
            "title": "2008 Crash",
            "description": "Pre-built crash scenario",
            "category": "market_crash",
            "blueprint_version_id": version_id,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["id"].startswith("scn_")
    assert body["payload"] == _valid_payload()


async def test_list_public_no_auth_and_category_filter(client: AsyncClient) -> None:
    account = await _register(client, "scen2@b.co")
    version_id = await _create_blueprint_version(client, account["headers"])
    await client.post(
        "/api/v1/scenarios",
        headers=account["headers"],
        json={
            "title": "Crash",
            "description": "D",
            "category": "market_crash",
            "blueprint_version_id": version_id,
        },
    )
    await client.post(
        "/api/v1/scenarios",
        headers=account["headers"],
        json={
            "title": "Pandemic",
            "description": "D",
            "category": "pandemic",
            "blueprint_version_id": version_id,
        },
    )

    # No auth token needed.
    resp = await client.get("/api/v1/scenarios?category=market_crash")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Crash"


async def test_featured_returns_only_featured(client: AsyncClient) -> None:
    account = await _register(client, "scen3@b.co")
    version_id = await _create_blueprint_version(client, account["headers"])
    resp = await client.post(
        "/api/v1/scenarios",
        headers=account["headers"],
        json={
            "title": "Featured One",
            "description": "D",
            "category": "custom",
            "blueprint_version_id": version_id,
        },
    )
    scenario_id = resp.json()["id"]

    # Mark featured directly in DB (admin-set).
    from app.db.session import async_session_factory
    from app.models.scenario import Scenario

    async with async_session_factory() as session:
        scenario = await session.get(Scenario, scenario_id)
        scenario.is_featured = True
        await session.commit()

    resp = await client.get("/api/v1/scenarios/featured")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == scenario_id


async def test_clone_creates_blueprint_in_caller_workspace(client: AsyncClient) -> None:
    author = await _register(client, "scen4@b.co")
    version_id = await _create_blueprint_version(client, author["headers"])
    resp = await client.post(
        "/api/v1/scenarios",
        headers=author["headers"],
        json={
            "title": "Clone Me",
            "description": "D",
            "category": "custom",
            "blueprint_version_id": version_id,
        },
    )
    scenario_id = resp.json()["id"]

    cloner = await _register(client, "scen4b@b.co")
    resp = await client.post(
        f"/api/v1/scenarios/{scenario_id}/clone",
        headers=cloner["headers"],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["blueprint_id"]
    assert body["blueprint_version_id"]

    # Appears in the cloner's blueprint list.
    bps = (await client.get(
        "/api/v1/blueprints", headers=cloner["headers"]
    )).json()
    assert any(bp["id"] == body["blueprint_id"] for bp in bps)

    # clones_count incremented by 1.
    detail = (await client.get(f"/api/v1/scenarios/{scenario_id}")).json()
    assert detail["clones_count"] == 1


async def test_get_private_scenario_404_for_outsider(client: AsyncClient) -> None:
    author = await _register(client, "scen5@b.co")
    version_id = await _create_blueprint_version(client, author["headers"])
    resp = await client.post(
        "/api/v1/scenarios",
        headers=author["headers"],
        json={
            "title": "Private",
            "description": "D",
            "category": "custom",
            "blueprint_version_id": version_id,
        },
    )
    scenario_id = resp.json()["id"]

    from app.db.session import async_session_factory
    from app.models.scenario import Scenario

    async with async_session_factory() as session:
        scenario = await session.get(Scenario, scenario_id)
        scenario.is_public = False
        await session.commit()

    outsider = await _register(client, "scen5b@b.co")
    resp = await client.get(
        f"/api/v1/scenarios/{scenario_id}",
        headers=outsider["headers"],
    )
    assert resp.status_code == 404

    # Author can still see it.
    resp = await client.get(
        f"/api/v1/scenarios/{scenario_id}",
        headers=author["headers"],
    )
    assert resp.status_code == 200


async def test_delete_foreign_scenario_403(client: AsyncClient) -> None:
    author = await _register(client, "scen6@b.co")
    version_id = await _create_blueprint_version(client, author["headers"])
    resp = await client.post(
        "/api/v1/scenarios",
        headers=author["headers"],
        json={
            "title": "Mine",
            "description": "D",
            "category": "custom",
            "blueprint_version_id": version_id,
        },
    )
    scenario_id = resp.json()["id"]

    outsider = await _register(client, "scen6b@b.co")
    resp = await client.delete(
        f"/api/v1/scenarios/{scenario_id}",
        headers=outsider["headers"],
    )
    assert resp.status_code == 403

    resp = await client.delete(
        f"/api/v1/scenarios/{scenario_id}",
        headers=author["headers"],
    )
    assert resp.status_code == 204
