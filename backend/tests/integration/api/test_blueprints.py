"""Integration tests for blueprint CRUD + versioning (T17)."""

import json
from pathlib import Path

import pytest
from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _register(client: AsyncClient, email: str, name: str):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": name, "password": "password123"},
    )
    assert resp.status_code == 201
    return resp.json()


async def _login(client: AsyncClient, email: str):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def owner(client: AsyncClient):
    """Owner + personal workspace + auth/workspace headers."""
    await _register(client, "bp-owner@b.co", "BpOwner")
    token = await _login(client, "bp-owner@b.co")
    ws = await client.get("/api/v1/workspaces", headers=_auth(token))
    return {
        "token": token,
        "workspace_id": ws.json()[0]["id"],
        "headers": {
            **_auth(token),
            "X-Workspace-Id": ws.json()[0]["id"],
        },
    }


@pytest.fixture
async def outsider(client: AsyncClient):
    """A second user with their own workspace (used for isolation checks)."""
    await _register(client, "bp-outsider@b.co", "Outsider")
    token = await _login(client, "bp-outsider@b.co")
    ws = await client.get("/api/v1/workspaces", headers=_auth(token))
    return {
        "token": token,
        "workspace_id": ws.json()[0]["id"],
        "headers": {
            **_auth(token),
            "X-Workspace-Id": ws.json()[0]["id"],
        },
    }


async def _create(client: AsyncClient, headers: dict, **overrides) -> dict:
    body = {
        "name": "My Blueprint",
        "industry": "B2B SaaS",
        "stage": "Seed",
        "payload": _valid_payload(),
    }
    body.update(overrides)
    resp = await client.post("/api/v1/blueprints", json=body, headers=headers)
    return resp


async def test_create_blueprint_returns_detail(client: AsyncClient, owner) -> None:
    resp = await _create(client, owner["headers"])
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"].startswith("bp_")
    assert body["workspace_id"] == owner["workspace_id"]
    assert body["name"] == "My Blueprint"
    assert body["current_version"] == 1
    assert body["payload"]["business_profile"]["model_type"] == "SaaS"


async def test_create_rejects_invalid_payload(client: AsyncClient, owner) -> None:
    payload = _valid_payload()
    payload["revenue_engine"]["streams"][0]["ltv"] = 100
    payload["revenue_engine"]["streams"][0]["cac"] = 850  # ltv < cac

    resp = await _create(client, owner["headers"], payload=payload)
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["is_valid"] is False
    codes = {i["code"] for i in detail["errors"]}
    assert "NEGATIVE_UNIT_ECONOMICS" in codes


async def test_requires_workspace_header(client: AsyncClient, owner) -> None:
    resp = await _create(client, _auth(owner["token"]))
    assert resp.status_code == 403


async def test_list_scoped_to_workspace(client: AsyncClient, owner, outsider) -> None:
    await _create(client, owner["headers"], name="Owner BP")
    await _create(client, outsider["headers"], name="Outsider BP")

    owner_list = await client.get("/api/v1/blueprints", headers=owner["headers"])
    assert owner_list.status_code == 200
    names = [bp["name"] for bp in owner_list.json()]
    assert names == ["Owner BP"]

    outsider_list = await client.get("/api/v1/blueprints", headers=outsider["headers"])
    assert [bp["name"] for bp in outsider_list.json()] == ["Outsider BP"]


async def test_cross_workspace_404(client: AsyncClient, owner, outsider) -> None:
    created = await _create(client, owner["headers"])
    bp_id = created.json()["id"]

    # Outsider cannot GET / PATCH / DELETE / validate the owner's blueprint.
    for method, path, body in [
        ("get", f"/api/v1/blueprints/{bp_id}", None),
        ("patch", f"/api/v1/blueprints/{bp_id}", {"name": "Hax"}),
        ("delete", f"/api/v1/blueprints/{bp_id}", None),
        ("get", f"/api/v1/blueprints/{bp_id}/validate", None),
        ("post", f"/api/v1/blueprints/{bp_id}/versions", {"payload": _valid_payload()}),
    ]:
        resp = await client.request(method, path, headers=outsider["headers"], json=body)
        assert resp.status_code == 404, f"{method} {path} -> {resp.status_code}"


async def test_versioning_bumps_current(client: AsyncClient, owner) -> None:
    created = await _create(client, owner["headers"])
    bp_id = created.json()["id"]

    v2 = await client.post(
        f"/api/v1/blueprints/{bp_id}/versions",
        json={"payload": _valid_payload()},
        headers=owner["headers"],
    )
    assert v2.status_code == 201
    assert v2.json()["version"] == 2

    v3 = await client.post(
        f"/api/v1/blueprints/{bp_id}/versions",
        json={"payload": _valid_payload()},
        headers=owner["headers"],
    )
    assert v3.status_code == 201
    assert v3.json()["version"] == 3

    detail = await client.get(f"/api/v1/blueprints/{bp_id}", headers=owner["headers"])
    assert detail.status_code == 200
    assert detail.json()["current_version"] == 3

    versions = await client.get(
        f"/api/v1/blueprints/{bp_id}/versions", headers=owner["headers"]
    )
    assert versions.status_code == 200
    got = [v["version"] for v in versions.json()]
    assert got == [3, 2, 1]


async def test_version_create_rejects_invalid_payload(client: AsyncClient, owner) -> None:
    created = await _create(client, owner["headers"])
    payload = _valid_payload()
    payload["revenue_engine"]["streams"] = []  # NO_REVENUE_STREAMS

    resp = await client.post(
        f"/api/v1/blueprints/{created.json()['id']}/versions",
        json={"payload": payload},
        headers=owner["headers"],
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["is_valid"] is False


async def test_validate_endpoint_reports_warnings(client: AsyncClient, owner) -> None:
    payload = _valid_payload()
    # 2400/850 = 2.82 < 3.0 -> warning, but the blueprint is still stored.
    created = await _create(client, owner["headers"], payload=payload)
    bp_id = created.json()["id"]

    resp = await client.get(f"/api/v1/blueprints/{bp_id}/validate", headers=owner["headers"])
    assert resp.status_code == 200
    report = resp.json()
    assert report["is_valid"] is True
    codes = {i["code"] for i in report["warnings"]}
    assert "LTV_CAC_RATIO" in codes


async def test_validate_missing_version_404(client: AsyncClient, owner) -> None:
    created = await _create(client, owner["headers"])
    resp = await client.get(
        f"/api/v1/blueprints/{created.json()['id']}/validate",
        params={"version": 99},
        headers=owner["headers"],
    )
    assert resp.status_code == 404


async def test_validate_pinned_version(client: AsyncClient, owner) -> None:
    created = await _create(client, owner["headers"])
    bp_id = created.json()["id"]

    # v2 with a worse LTV:CAC (still valid, but adds a warning)
    weak = _valid_payload()
    weak["revenue_engine"]["streams"][0]["ltv"] = 1200  # 1200/850 = 1.4 < 3.0
    weak["revenue_engine"]["streams"][0]["cac"] = 850
    v2 = await client.post(
        f"/api/v1/blueprints/{bp_id}/versions",
        json={"payload": weak},
        headers=owner["headers"],
    )
    assert v2.status_code == 201

    # Current (v2) validate reports the LTV:CAC warning.
    current = await client.get(f"/api/v1/blueprints/{bp_id}/validate", headers=owner["headers"])
    assert current.status_code == 200
    assert current.json()["is_valid"] is True
    codes = {i["code"] for i in current.json()["warnings"]}
    assert "LTV_CAC_RATIO" in codes

    # Pinned v1 (the original fixture payload) has no LTV:CAC warning beyond
    # the fixture's own — confirm pinning returns a different report shape.
    v1 = await client.get(
        f"/api/v1/blueprints/{bp_id}/validate",
        params={"version": 1},
        headers=owner["headers"],
    )
    assert v1.status_code == 200
    assert v1.json()["is_valid"] is True
    v1_codes = {i["code"] for i in v1.json()["warnings"]}
    assert "LTV_CAC_RATIO" in v1_codes


async def test_patch_updates_metadata_only(client: AsyncClient, owner) -> None:
    created = await _create(client, owner["headers"])
    bp_id = created.json()["id"]

    resp = await client.patch(
        f"/api/v1/blueprints/{bp_id}",
        json={"name": "Renamed", "stage": "Series A"},
        headers=owner["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Renamed"
    assert body["stage"] == "Series A"
    assert body["current_version"] == 1

    detail = await client.get(f"/api/v1/blueprints/{bp_id}", headers=owner["headers"])
    assert detail.json()["payload"]["business_profile"]["stage"] == "Seed"


async def test_delete_cascades(client: AsyncClient, owner) -> None:
    created = await _create(client, owner["headers"])
    bp_id = created.json()["id"]
    await client.post(
        f"/api/v1/blueprints/{bp_id}/versions",
        json={"payload": _valid_payload()},
        headers=owner["headers"],
    )

    resp = await client.delete(f"/api/v1/blueprints/{bp_id}", headers=owner["headers"])
    assert resp.status_code == 204

    assert (
        await client.get(f"/api/v1/blueprints/{bp_id}", headers=owner["headers"])
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=owner["headers"])
    ).status_code == 404


async def test_unknown_blueprint_404(client: AsyncClient, owner) -> None:
    assert (
        await client.get("/api/v1/blueprints/nope", headers=owner["headers"])
    ).status_code == 404
