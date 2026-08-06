"""Integration tests for POST /api/v1/users/me/password (T38)."""

from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Pw", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return login.json()["access_token"]


async def test_change_password_returns_204(client: AsyncClient) -> None:
    token = await _register_and_login(client, "pw1@b.co")
    resp = await client.post(
        "/api/v1/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "password123", "new_password": "newpassword456"},
    )
    assert resp.status_code == 204


async def test_change_password_wrong_current_returns_400(client: AsyncClient) -> None:
    token = await _register_and_login(client, "pw2@b.co")
    resp = await client.post(
        "/api/v1/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "wrongpass1", "new_password": "newpassword456"},
    )
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Current password is incorrect"}


async def test_new_password_works_on_login(client: AsyncClient) -> None:
    token = await _register_and_login(client, "pw3@b.co")
    resp = await client.post(
        "/api/v1/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "password123", "new_password": "brandnewpass9"},
    )
    assert resp.status_code == 204

    # Old password fails.
    old = await client.post(
        "/api/v1/auth/login", json={"email": "pw3@b.co", "password": "password123"}
    )
    assert old.status_code == 401

    # New password works.
    new_login = await client.post(
        "/api/v1/auth/login", json={"email": "pw3@b.co", "password": "brandnewpass9"}
    )
    assert new_login.status_code == 200


async def test_change_password_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": "password123", "new_password": "newpassword456"},
    )
    assert resp.status_code == 401
