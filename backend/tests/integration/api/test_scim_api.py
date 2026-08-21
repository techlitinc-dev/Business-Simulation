"""Integration tests for SCIM 2.0 provisioning + SSO OIDC endpoints."""

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
    account = await _register_workspace(client, "scim1@b.co")

    resp = await client.post(
        f"/api/v1/scim/v2/Users?workspace_id={account['workspace_id']}",
        json={
            "userName": "newuser@example.com",
            "displayName": "New User",
            "active": True,
        },
        headers=SCIM_HEADERS,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["userName"] == "newuser@example.com"
    assert data["displayName"] == "New User"
    assert data["active"] is True
    assert data["schemas"] == ["urn:ietf:params:scim:schemas:core:2.0:User"]

    # The provisioned user is a member of the workspace.
    members = await client.get(
        f"/api/v1/workspaces/{account['workspace_id']}/members",
        headers=account["headers"],
    )
    assert members.status_code == 200
    emails = [m["email"] for m in members.json()]
    assert "newuser@example.com" in emails


async def test_scim_provision_is_idempotent(client: AsyncClient) -> None:
    account = await _register_workspace(client, "scim2@b.co")
    payload = {"userName": "again@example.com", "displayName": "Again", "active": True}

    first = await client.post(
        f"/api/v1/scim/v2/Users?workspace_id={account['workspace_id']}",
        json=payload,
        headers=SCIM_HEADERS,
    )
    second = await client.post(
        f"/api/v1/scim/v2/Users?workspace_id={account['workspace_id']}",
        json=payload,
        headers=SCIM_HEADERS,
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


async def test_scim_invalid_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/scim/v2/Users?workspace_id=00000000-0000-0000-0000-000000000000",
        json={"userName": "test@example.com", "active": True},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


async def test_scim_deprovision_user(client: AsyncClient) -> None:
    account = await _register_workspace(client, "scim3@b.co")
    provisioned = await client.post(
        f"/api/v1/scim/v2/Users?workspace_id={account['workspace_id']}",
        json={"userName": "depro@example.com", "active": True},
        headers=SCIM_HEADERS,
    )
    user_id = provisioned.json()["id"]

    resp = await client.delete(f"/api/v1/scim/v2/Users/{user_id}", headers=SCIM_HEADERS)
    assert resp.status_code == 204

    # Deactivating again is a no-op, not an error.
    again = await client.delete(f"/api/v1/scim/v2/Users/{user_id}", headers=SCIM_HEADERS)
    assert again.status_code == 204


async def test_scim_patch_deactivate(client: AsyncClient) -> None:
    account = await _register_workspace(client, "scim4@b.co")
    provisioned = await client.post(
        f"/api/v1/scim/v2/Users?workspace_id={account['workspace_id']}",
        json={"userName": "patch@example.com", "active": True},
        headers=SCIM_HEADERS,
    )
    user_id = provisioned.json()["id"]

    resp = await client.patch(
        f"/api/v1/scim/v2/Users/{user_id}", json={"active": False}, headers=SCIM_HEADERS
    )
    assert resp.status_code == 200
    assert resp.json()["active"] is False


async def test_oidc_callback_stub(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/sso/oidc/callback?code=abc12345")
    assert resp.status_code == 200
    assert "OIDC callback received" in resp.json()["message"]


async def test_oidc_exchange_creates_user(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/sso/oidc/exchange",
        json={
            "email": "oidc@example.com",
            "external_id": "idp-123",
            "display_name": "Oidc User",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["user_id"]

    # Second exchange links the same account (same user id).
    again = await client.post(
        "/api/v1/sso/oidc/exchange",
        json={"email": "oidc@example.com", "external_id": "idp-123"},
    )
    assert again.json()["user_id"] == data["user_id"]
