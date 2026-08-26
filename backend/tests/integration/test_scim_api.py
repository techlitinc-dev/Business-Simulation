"""Integration tests for SCIM 2.0 provisioning + SSO OIDC endpoints (Day 27 spec)."""

from __future__ import annotations

from app.core.config import get_settings
from httpx import AsyncClient

SCIM_HEADERS = {"Authorization": f"Bearer {get_settings().scim_token}"}


async def _register_workspace(client: AsyncClient, email: str) -> dict[str, str]:
    """Register a user and create a workspace, returning auth headers + ws id."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Scim", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    ws = await client.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "SCIM Workspace"},
    )
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "workspace_id": ws.json()["id"],
    }


async def test_scim_provision_user(client: AsyncClient) -> None:
    account = await _register_workspace(client, "spec1@b.co")

    resp = await client.post(
        f"/api/v1/scim/v2/Users?workspace_id={account['workspace_id']}",
        json={
            "userName": "scimspec@example.com",
            "displayName": "SCIM Spec",
            "active": True,
        },
        headers=SCIM_HEADERS,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["userName"] == "scimspec@example.com"
    assert data["active"] is True


async def test_scim_invalid_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/scim/v2/Users?workspace_id=00000000-0000-0000-0000-000000000000",
        json={"userName": "test@example.com", "active": True},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


async def test_scim_deprovision_user(client: AsyncClient) -> None:
    account = await _register_workspace(client, "spec2@b.co")
    provisioned = await client.post(
        f"/api/v1/scim/v2/Users?workspace_id={account['workspace_id']}",
        json={"userName": "specdepro@example.com", "active": True},
        headers=SCIM_HEADERS,
    )
    user_id = provisioned.json()["id"]

    resp = await client.delete(
        f"/api/v1/scim/v2/Users/{user_id}", headers=SCIM_HEADERS
    )
    assert resp.status_code == 204


async def test_oidc_callback_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/sso/oidc/callback?code=abc12345")
    assert resp.status_code == 200
    assert "OIDC callback received" in resp.json()["message"]


async def test_oidc_exchange_creates_user(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/sso/oidc/exchange",
        json={
            "email": "specoidc@example.com",
            "external_id": "idp-spec",
            "display_name": "Spec Oidc",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["user_id"]
    assert data["access_token"]
