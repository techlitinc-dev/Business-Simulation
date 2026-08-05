"""Integration tests for the auth + users endpoints."""

from app.core.security import decode_token
from app.workers.email_tasks import create_verification_token
from httpx import AsyncClient


async def test_register_returns_201_with_user(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.co", "name": "Alice", "password": "password123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert set(body) == {"id", "email", "name", "is_verified"}
    assert body["email"] == "a@b.co"
    assert body["name"] == "Alice"
    assert body["is_verified"] is False


async def test_register_normalizes_email_and_hashes_password(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "UPPER@Example.com", "name": "U", "password": "password123"},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "upper@example.com"


async def test_register_duplicate_email_returns_409(client: AsyncClient) -> None:
    payload = {"email": "dup@b.co", "name": "D", "password": "password123"}
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


async def test_login_success_returns_token_pair(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "l@b.co", "name": "L", "password": "password123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "l@b.co", "password": "password123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"access_token", "refresh_token", "token_type"}
    assert body["token_type"] == "bearer"
    claims = decode_token(body["access_token"])
    assert claims["type"] == "access"


async def test_login_wrong_password_and_unknown_email_identical_401(
    client: AsyncClient,
) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "w@b.co", "name": "W", "password": "password123"},
    )
    r1 = await client.post(
        "/api/v1/auth/login", json={"email": "w@b.co", "password": "wrongpass1"}
    )
    r2 = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@b.co", "password": "password123"}
    )
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()


async def test_refresh_rotates_tokens(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "r@b.co", "name": "R", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "r@b.co", "password": "password123"}
    )
    old_refresh = login.json()["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert resp.status_code == 200
    new_pair = resp.json()
    assert new_pair["access_token"] != login.json()["access_token"]
    assert new_pair["refresh_token"] != old_refresh
    assert decode_token(new_pair["access_token"])["type"] == "access"


async def test_refresh_rejects_access_token(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "x@b.co", "name": "X", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "x@b.co", "password": "password123"}
    )
    access = login.json()["access_token"]
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_me_returns_caller(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "me@b.co", "name": "Me", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "me@b.co", "password": "password123"}
    )
    token = login.json()["access_token"]
    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@b.co"
    assert body["name"] == "Me"


async def test_verify_email_sets_verified(client: AsyncClient) -> None:
    user = (await client.post(
        "/api/v1/auth/register",
        json={"email": "ver@b.co", "name": "Ver", "password": "password123"},
    )).json()
    assert user["is_verified"] is False

    token = create_verification_token(str(user["id"]))
    resp = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert resp.status_code == 200
    assert resp.json() == {"detail": "email verified"}

    # /users/me now reports is_verified: true
    login = await client.post(
        "/api/v1/auth/login", json={"email": "ver@b.co", "password": "password123"}
    )
    me = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.json()["is_verified"] is True


async def test_verify_email_rejects_tampered_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/verify-email", json={"token": "garbage-token"}
    )
    assert resp.status_code == 400


async def test_verify_email_rejects_expired_token(client: AsyncClient) -> None:
    import itsdangerous.timed as _timed
    from app.core.config import get_settings
    from app.workers.email_tasks import VERIFY_SALT
    from itsdangerous import URLSafeTimedSerializer

    settings = get_settings()
    serializer = URLSafeTimedSerializer(settings.jwt_secret_key, salt=VERIFY_SALT)
    # Sign with 2001 time, then restore before the request so verification
    # sees real time and treats the token as expired.
    orig = _timed.time.time
    _timed.time.time = lambda: 1000000000  # type: ignore[method-assign]
    try:
        expired = serializer.dumps("user-id")
    finally:
        _timed.time.time = orig  # type: ignore[method-assign]

    resp = await client.post("/api/v1/auth/verify-email", json={"token": expired})
    assert resp.status_code == 400
