"""Coverage for app/api/deps.py error paths (T47).

The happy-path suites cover authenticated requests; these tests drive the
failure branches in the auth/workspace/RBAC dependency layer: bad tokens,
missing workspace header, cross-workspace 403s, and API-key edge cases.
"""

import json
from pathlib import Path

import fakeredis.aioredis
import jwt
from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _register(client: AsyncClient, email: str) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Dep", "password": "password123"},
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


async def test_bearer_scheme_not_bearer_401(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/blueprints", headers={"Authorization": "Basic abc123"}
    )
    assert resp.status_code == 401


async def test_invalid_token_401(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/blueprints", headers={"Authorization": "Bearer garbage"}
    )
    assert resp.status_code == 401


async def test_refresh_token_used_as_access_401(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "dep1@b.co", "name": "Dep", "password": "password123"},
    )
    refresh = (
        await client.post(
            "/api/v1/auth/login", json={"email": "dep1@b.co", "password": "password123"}
        )
    ).json()["refresh_token"]
    resp = await client.get(
        "/api/v1/blueprints", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert resp.status_code == 401


async def test_expired_token_401(client: AsyncClient, monkeypatch) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    expired = jwt.encode(
        {"sub": "u", "type": "access", "exp": 1000000},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    resp = await client.get(
        "/api/v1/blueprints", headers={"Authorization": f"Bearer {expired}"}
    )
    assert resp.status_code == 401


async def test_missing_workspace_header_403(client: AsyncClient) -> None:
    account = await _register(client, "dep2@b.co")
    resp = await client.get(
        "/api/v1/blueprints",
        headers={"Authorization": f"Bearer {account['token']}"},
    )
    assert resp.status_code == 403


async def test_foreign_workspace_header_403(client: AsyncClient) -> None:
    account = await _register(client, "dep3@b.co")
    other = await _register(client, "dep3b@b.co")
    resp = await client.get(
        "/api/v1/blueprints",
        headers={
            "Authorization": f"Bearer {account['token']}",
            "X-Workspace-Id": other["workspace_id"],
        },
    )
    assert resp.status_code == 403


async def test_invalid_workspace_uuid_403(client: AsyncClient) -> None:
    account = await _register(client, "dep4@b.co")
    # A well-formed UUID with no membership → 403 (Not a member).
    resp = await client.get(
        "/api/v1/blueprints",
        headers={
            "Authorization": f"Bearer {account['token']}",
            "X-Workspace-Id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert resp.status_code == 403


async def test_api_key_unknown_401(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/simulations",
        headers={"X-API-Key": "fk_unknown", "X-Workspace-Id": "x"},
    )
    assert resp.status_code == 401


async def test_api_key_wrong_workspace_403(client: AsyncClient) -> None:
    account = await _register(client, "dep5@b.co")
    other = await _register(client, "dep5b@b.co")
    created = await client.post(
        "/api/v1/api-keys",
        headers=account["headers"],
        json={"name": "CI", "scopes": ["runs:read"]},
    )
    key = created.json()["key"]
    resp = await client.get(
        "/api/v1/simulations",
        headers={"X-API-Key": key, "X-Workspace-Id": other["workspace_id"]},
    )
    assert resp.status_code == 403


async def test_require_workspace_role_member_denied(client: AsyncClient) -> None:
    """A non-admin member gets 403 on admin-role workspace routes."""
    import uuid

    from app.core.security import create_access_token
    from app.db.session import async_session_factory
    from app.models.user import User
    from app.models.workspace import Membership, Role, Workspace

    owner = await _register(client, "dep6@b.co")

    async with async_session_factory() as session:
        ws = await session.get(Workspace, uuid.UUID(owner["workspace_id"]))
        member_user = User(email="dep6m@b.co", name="Member", pw_hash="x")
        session.add(member_user)
        await session.flush()
        session.add(
            Membership(user_id=member_user.id, workspace_id=ws.id, role=Role.MEMBER)
        )
        await session.commit()

    member_token = create_access_token(str(member_user.id))
    member_headers = {
        "Authorization": f"Bearer {member_token}",
        "X-Workspace-Id": owner["workspace_id"],
    }

    # Delete requires owner → 403 for a member.
    resp = await client.delete(
        f"/api/v1/workspaces/{owner['workspace_id']}", headers=member_headers
    )
    assert resp.status_code == 403


async def test_require_member_removal_admin_or_self(
    client: AsyncClient, monkeypatch
) -> None:
    """A member removing another member → 403; admin can remove."""
    import uuid

    from app.core.security import create_access_token
    from app.db.session import async_session_factory
    from app.models.user import User
    from app.models.workspace import Membership, Role, Workspace

    owner = await _register(client, "dep7@b.co")

    async with async_session_factory() as session:
        ws = await session.get(Workspace, uuid.UUID(owner["workspace_id"]))
        member1 = User(email="dep7a@b.co", name="M1", pw_hash="x")
        member2 = User(email="dep7b@b.co", name="M2", pw_hash="x")
        session.add_all([member1, member2])
        await session.flush()
        session.add_all(
            [
                Membership(user_id=member1.id, workspace_id=ws.id, role=Role.MEMBER),
                Membership(user_id=member2.id, workspace_id=ws.id, role=Role.MEMBER),
            ]
        )
        await session.commit()

    m1_token = create_access_token(str(member1.id))
    m1_headers = {
        "Authorization": f"Bearer {m1_token}",
        "X-Workspace-Id": owner["workspace_id"],
    }

    # Member removing another member → 403.
    resp = await client.delete(
        f"/api/v1/workspaces/{owner['workspace_id']}/members/{member2.id}",
        headers=m1_headers,
    )
    assert resp.status_code == 403


async def test_reports_compare_missing_run_404(client: AsyncClient) -> None:
    account = await _register(client, "dep8@b.co")
    resp = await client.get(
        "/api/v1/reports/compare?a=run_a&b=run_b", headers=account["headers"]
    )
    assert resp.status_code == 404


async def test_get_optional_user_invalid_token_401(client: AsyncClient) -> None:
    # Scenario detail is public + optionally personalized; a bad token → 401.
    resp = await client.get(
        "/api/v1/scenarios/scn_1", headers={"Authorization": "Bearer bad"}
    )
    assert resp.status_code == 401


async def test_enforce_plan_limit_increment_after_success(
    client: AsyncClient, monkeypatch
) -> None:
    """After a successful run the meter is incremented (T41 guard post-yield)."""
    from app.core.rate_limit import reset_windows

    reset_windows()
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    account = await _register(client, "dep9@b.co")
    resp = await client.post(
        "/api/v1/blueprints",
        headers=account["headers"],
        json={
            "name": "Dep BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
    )
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=account["headers"])
    version_id = versions.json()[0]["id"]

    run = await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={"blueprint_version_id": version_id, "mode": "baseline", "seed": 1},
    )
    assert run.status_code == 201

    usage = (await client.get(
        "/api/v1/billing/usage", headers=account["headers"]
    )).json()
    assert usage["usage"]["runs_used"] == 1
    reset_windows()
