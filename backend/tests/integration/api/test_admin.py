"""Integration tests for admin endpoints (T46)."""

from httpx import AsyncClient


async def _register(client: AsyncClient, email: str) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Adm", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}}


async def _set_admin(client: AsyncClient, email: str) -> None:
    from app.db.session import async_session_factory
    from app.models.user import User

    async with async_session_factory() as session:
        from sqlalchemy import select

        user = await session.scalar(select(User).where(User.email == email))
        user.is_admin = True
        await session.commit()


async def test_admin_stats_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/admin/stats")
    assert resp.status_code == 401


async def test_admin_stats_forbidden_for_non_admin(client: AsyncClient) -> None:
    account = await _register(client, "adm1@b.co")
    resp = await client.get("/api/v1/admin/stats", headers=account["headers"])
    assert resp.status_code == 403


async def test_admin_stats_returns_all_fields(client: AsyncClient) -> None:
    await _register(client, "adm2@b.co")
    await _set_admin(client, "adm2@b.co")
    login = await client.post(
        "/api/v1/auth/login", json={"email": "adm2@b.co", "password": "password123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get("/api/v1/admin/stats", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_users"] >= 1
    assert set(body.keys()) == {
        "total_users",
        "users_last_30d",
        "total_workspaces",
        "workspaces_last_30d",
        "subscriptions_by_tier",
        "mrr_estimate_usd",
        "runs_this_month",
        "monte_carlo_ticks_this_month",
        "llm_tokens_this_month",
    }
    assert set(body["subscriptions_by_tier"].keys()) == {"free", "pro", "enterprise"}


async def test_admin_users_search(client: AsyncClient) -> None:
    await _register(client, "alice@b.co")
    await _register(client, "bob@b.co")
    await _set_admin(client, "alice@b.co")
    login = await client.post(
        "/api/v1/auth/login", json={"email": "alice@b.co", "password": "password123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get("/api/v1/admin/users?q=ALICE", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "alice@b.co"


async def test_admin_workspaces_list(client: AsyncClient) -> None:
    await _register(client, "adm3@b.co")
    await _set_admin(client, "adm3@b.co")
    login = await client.post(
        "/api/v1/auth/login", json={"email": "adm3@b.co", "password": "password123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get("/api/v1/admin/workspaces", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert body["items"][0]["name"].endswith("'s Workspace")
    assert body["items"][0]["member_count"] == 1
