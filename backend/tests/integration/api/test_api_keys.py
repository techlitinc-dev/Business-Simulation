"""Integration tests for API key endpoints + X-API-Key auth (T45)."""

import json
from pathlib import Path

from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _register(client: AsyncClient, email: str) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Key", "password": "password123"},
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


async def test_create_key_returns_plaintext(client: AsyncClient) -> None:
    account = await _register(client, "key1@b.co")
    resp = await client.post(
        "/api/v1/api-keys",
        headers=account["headers"],
        json={"name": "CI", "scopes": ["runs:read", "reports:read"]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["key"].startswith("fk_")
    assert body["prefix"] == body["key"][:12]
    assert body["id"].startswith("key_")


async def test_list_keys_no_hash_or_plaintext(client: AsyncClient) -> None:
    account = await _register(client, "key2@b.co")
    await client.post(
        "/api/v1/api-keys",
        headers=account["headers"],
        json={"name": "CI", "scopes": ["runs:read"]},
    )
    resp = await client.get("/api/v1/api-keys", headers=account["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert "key_hash" not in body[0]
    assert "key" not in body[0]


async def test_revoked_key_401(client: AsyncClient) -> None:
    account = await _register(client, "key3@b.co")
    created = await client.post(
        "/api/v1/api-keys",
        headers=account["headers"],
        json={"name": "CI", "scopes": ["runs:read"]},
    )
    key = created.json()["key"]
    key_id = created.json()["id"]

    # Works before revoke.
    await client.delete(f"/api/v1/api-keys/{key_id}", headers=account["headers"])

    # Revoked → 401.
    resp = await client.get(
        "/api/v1/simulations", headers={"X-API-Key": key, "X-Workspace-Id": account["workspace_id"]}
    )
    assert resp.status_code == 401


async def test_create_key_requires_admin(client: AsyncClient) -> None:
    owner = await _register(client, "key4@b.co")

    # Add a member and try creating a key as them.
    import uuid

    from app.db.session import async_session_factory
    from app.models.workspace import Membership, Role, Workspace

    async with async_session_factory() as session:
        ws = await session.get(Workspace, uuid.UUID(owner["workspace_id"]))
        # Member user.
        member_user = None
        from app.models.user import User

        member_user = User(
            email="keymember@b.co",
            name="Member",
            pw_hash="x",
        )
        session.add(member_user)
        await session.flush()
        session.add(
            Membership(
                user_id=member_user.id, workspace_id=ws.id, role=Role.MEMBER
            )
        )
        await session.commit()

    from app.core.security import create_access_token

    member_token = create_access_token(str(member_user.id))
    resp = await client.post(
        "/api/v1/api-keys",
        headers={
            "Authorization": f"Bearer {member_token}",
            "X-Workspace-Id": owner["workspace_id"],
        },
        json={"name": "Nope", "scopes": ["runs:read"]},
    )
    assert resp.status_code == 403


async def test_api_key_authenticates_simulations(client: AsyncClient) -> None:
    account = await _register(client, "key5@b.co")
    created = await client.post(
        "/api/v1/api-keys",
        headers=account["headers"],
        json={"name": "CI", "scopes": ["runs:read", "blueprints:read"]},
    )
    key = created.json()["key"]

    resp = await client.get(
        "/api/v1/simulations",
        headers={"X-API-Key": key, "X-Workspace-Id": account["workspace_id"]},
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_rate_limit_429(client: AsyncClient) -> None:
    from app.core.rate_limit import reset_windows

    reset_windows()
    account = await _register(client, "key6@b.co")
    created = await client.post(
        "/api/v1/api-keys",
        headers=account["headers"],
        json={"name": "CI", "scopes": ["runs:read"], "rate_limit_rpm": 2},
    )
    key = created.json()["key"]

    headers = {"X-API-Key": key, "X-Workspace-Id": account["workspace_id"]}
    for _ in range(2):
        resp = await client.get("/api/v1/simulations", headers=headers)
        assert resp.status_code == 200

    # 3rd request within the window → 429 with Retry-After.
    resp = await client.get("/api/v1/simulations", headers=headers)
    assert resp.status_code == 429
    assert resp.headers.get("Retry-After")
    reset_windows()
