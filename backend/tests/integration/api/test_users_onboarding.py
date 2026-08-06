"""Integration tests for the T36 onboarding PATCH flow on /users/me."""

from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Onb", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return login.json()["access_token"]


async def test_me_exposes_onboarding_fields_defaults(client: AsyncClient) -> None:
    token = await _register_and_login(client, "onb1@b.co")
    resp = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["industry"] is None
    assert body["stage"] is None
    assert body["primary_fear"] is None
    assert body["onboarding_completed"] is False


async def test_patch_me_persists_fields_and_flips_onboarding(client: AsyncClient) -> None:
    token = await _register_and_login(client, "onb2@b.co")
    resp = await client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "industry": "SaaS",
            "stage": "Pre-Seed",
            "primary_fear": "My CAC is too high",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["industry"] == "SaaS"
    assert body["stage"] == "Pre-Seed"
    assert body["primary_fear"] == "My CAC is too high"
    assert body["onboarding_completed"] is True

    # GET /users/me reflects the persisted values.
    me = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["onboarding_completed"] is True
    assert me.json()["industry"] == "SaaS"


async def test_patch_me_partial_update_keeps_onboarding_incomplete(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, "onb3@b.co")
    resp = await client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"industry": "Fintech"},
    )
    assert resp.status_code == 200
    assert resp.json()["industry"] == "Fintech"
    assert resp.json()["onboarding_completed"] is False


async def test_patch_me_updates_name(client: AsyncClient) -> None:
    token = await _register_and_login(client, "onb4@b.co")
    resp = await client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "  New Name  "},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
