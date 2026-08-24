"""Integration tests for workspace endpoints, RBAC, and invites."""


from datetime import UTC

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str, name: str, password: str = "password123"):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": name, "password": password},
    )
    assert resp.status_code == 201
    return resp.json()


async def _login(client: AsyncClient, email: str, password: str = "password123"):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200
    return resp.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def alice(client: AsyncClient):
    """Alice + her personal workspace."""
    user = await _register(client, "alice@b.co", "Alice")
    tokens = await _login(client, "alice@b.co")
    ws = await client.get("/api/v1/workspaces", headers=_auth(tokens["access_token"]))
    return {"user": user, "tokens": tokens, "workspace": ws.json()[0]}


async def test_register_auto_creates_personal_workspace(client: AsyncClient) -> None:
    user = await _register(client, "ws@b.co", "Workspacey")
    tokens = await _login(client, "ws@b.co")
    resp = await client.get("/api/v1/workspaces", headers=_auth(tokens["access_token"]))
    assert resp.status_code == 200
    workspaces = resp.json()
    assert len(workspaces) == 1
    assert workspaces[0]["name"] == "Workspacey's Workspace"
    assert workspaces[0]["role"] == "owner"
    assert workspaces[0]["id"] != user["id"]


async def test_create_workspace_makes_owner(client: AsyncClient) -> None:
    await _register(client, "cw@b.co", "CreateW")
    tokens = await _login(client, "cw@b.co")
    resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "My Second Space"},
        headers=_auth(tokens["access_token"]),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "My Second Space"
    assert body["role"] == "owner"
    assert body["slug"]

    listing = await client.get(
        "/api/v1/workspaces", headers=_auth(tokens["access_token"])
    )
    assert len(listing.json()) == 2


async def test_member_cannot_patch_or_invite(client: AsyncClient) -> None:
    await _register(client, "a2@b.co", "A2")
    atok = (await _login(client, "a2@b.co"))["access_token"]
    ws_id = (await client.get("/api/v1/workspaces", headers=_auth(atok))).json()[0]["id"]

    # Bob joins via invite as member
    invite = await client.post(
        f"/api/v1/workspaces/{ws_id}/invites",
        json={"email": "bob@b.co", "role": "member"},
        headers=_auth(atok),
    )
    await _register(client, "bob@b.co", "Bob")
    btok = (await _login(client, "bob@b.co"))["access_token"]
    token = invite.json()["invite_url"].split("token=")[1]
    await client.post(f"/api/v1/invites/{token}/accept", headers=_auth(btok))

    # member can GET workspace + members
    assert (
        await client.get(f"/api/v1/workspaces/{ws_id}", headers=_auth(btok))
    ).status_code == 200
    assert (
        await client.get(f"/api/v1/workspaces/{ws_id}/members", headers=_auth(btok))
    ).status_code == 200

    # member cannot PATCH, invite, or change roles
    assert (
        await client.patch(
            f"/api/v1/workspaces/{ws_id}", json={"name": "Hax"}, headers=_auth(btok)
        )
    ).status_code == 403
    assert (
        await client.post(
            f"/api/v1/workspaces/{ws_id}/invites",
            json={"email": "x@b.co", "role": "member"},
            headers=_auth(btok),
        )
    ).status_code == 403


async def test_admin_cannot_delete_workspace(client: AsyncClient) -> None:
    await _register(client, "own@b.co", "Owner")
    otok = (await _login(client, "own@b.co"))["access_token"]
    ws_id = (await client.get("/api/v1/workspaces", headers=_auth(otok))).json()[0]["id"]

    invite = await client.post(
        f"/api/v1/workspaces/{ws_id}/invites",
        json={"email": "adm@b.co", "role": "admin"},
        headers=_auth(otok),
    )
    await _register(client, "adm@b.co", "Admin")
    atok = (await _login(client, "adm@b.co"))["access_token"]
    token = invite.json()["invite_url"].split("token=")[1]
    await client.post(f"/api/v1/invites/{token}/accept", headers=_auth(atok))

    # admin can PATCH, cannot DELETE
    assert (
        await client.patch(
            f"/api/v1/workspaces/{ws_id}", json={"name": "Renamed"}, headers=_auth(atok)
        )
    ).status_code == 200
    assert (
        await client.delete(f"/api/v1/workspaces/{ws_id}", headers=_auth(atok))
    ).status_code == 403
    # owner can DELETE
    assert (
        await client.delete(f"/api/v1/workspaces/{ws_id}", headers=_auth(otok))
    ).status_code == 204


async def test_outsider_gets_403_on_workspace_routes(client: AsyncClient) -> None:
    await _register(client, "o1@b.co", "O1")
    t1 = (await _login(client, "o1@b.co"))["access_token"]
    ws_id = (await client.get("/api/v1/workspaces", headers=_auth(t1))).json()[0]["id"]

    await _register(client, "o2@b.co", "O2")
    t2 = (await _login(client, "o2@b.co"))["access_token"]

    for method, path in [
        ("get", f"/api/v1/workspaces/{ws_id}"),
        ("patch", f"/api/v1/workspaces/{ws_id}"),
        ("delete", f"/api/v1/workspaces/{ws_id}"),
        ("get", f"/api/v1/workspaces/{ws_id}/members"),
        ("post", f"/api/v1/workspaces/{ws_id}/invites"),
    ]:
        resp = await client.request(
            method, path, headers=_auth(t2), json={"name": "x", "email": "x@b.co"}
            if method in ("patch", "post")
            else None,
        )
        assert resp.status_code == 403, f"{method} {path} -> {resp.status_code}"


async def test_full_invite_round_trip(client: AsyncClient) -> None:
    await _register(client, "inv@b.co", "Invit")
    itok = (await _login(client, "inv@b.co"))["access_token"]
    ws_id = (await client.get("/api/v1/workspaces", headers=_auth(itok))).json()[0]["id"]

    invite_resp = await client.post(
        f"/api/v1/workspaces/{ws_id}/invites",
        json={"email": "invitee@b.co", "role": "member"},
        headers=_auth(itok),
    )
    assert invite_resp.status_code == 201
    invite = invite_resp.json()
    assert invite["role"] == "member"
    token = invite["invite_url"].split("token=")[1]

    await _register(client, "invitee@b.co", "Invitee")
    etok = (await _login(client, "invitee@b.co"))["access_token"]

    accept = await client.post(f"/api/v1/invites/{token}/accept", headers=_auth(etok))
    assert accept.status_code == 200
    assert accept.json()["workspace_id"] == ws_id
    assert accept.json()["role"] == "member"

    # invitee appears in members list
    members = await client.get(
        f"/api/v1/workspaces/{ws_id}/members", headers=_auth(etok)
    )
    emails = {m["email"]: m["role"] for m in members.json()}
    assert emails == {"inv@b.co": "owner", "invitee@b.co": "member"}

    # accepting twice -> 409
    again = await client.post(f"/api/v1/invites/{token}/accept", headers=_auth(etok))
    assert again.status_code == 409


async def test_expired_invite_returns_410(client: AsyncClient) -> None:
    await _register(client, "ex@b.co", "Exp")
    etok = (await _login(client, "ex@b.co"))["access_token"]
    ws_id = (await client.get("/api/v1/workspaces", headers=_auth(etok))).json()[0]["id"]

    invite = await client.post(
        f"/api/v1/workspaces/{ws_id}/invites",
        json={"email": "ghost@b.co", "role": "member"},
        headers=_auth(etok),
    )
    token = invite.json()["invite_url"].split("token=")[1]

    await _register(client, "ghost@b.co", "Ghost")
    gtok = (await _login(client, "ghost@b.co"))["access_token"]

    # Expire the invite directly in the DB via the app's session.
    from datetime import datetime

    from app.db.session import async_session_factory
    from app.models.workspace import Invite
    from sqlalchemy import update as sa_update

    async with async_session_factory() as session:
        await session.execute(
            sa_update(Invite)
            .where(Invite.token == token)
            .values(expires_at=datetime(2020, 1, 1, tzinfo=UTC))
        )
        await session.commit()

    resp = await client.post(f"/api/v1/invites/{token}/accept", headers=_auth(gtok))
    assert resp.status_code == 410


async def test_remove_last_owner_returns_409(client: AsyncClient) -> None:
    await _register(client, "lo@b.co", "LastOwner")
    lot = (await _login(client, "lo@b.co"))["access_token"]
    ws_id = (await client.get("/api/v1/workspaces", headers=_auth(lot))).json()[0]["id"]
    me = (await client.get("/api/v1/users/me", headers=_auth(lot))).json()

    resp = await client.delete(
        f"/api/v1/workspaces/{ws_id}/members/{me['id']}", headers=_auth(lot)
    )
    assert resp.status_code == 409


async def test_member_can_remove_themselves(client: AsyncClient) -> None:
    await _register(client, "sr@b.co", "SelfRemove")
    stok = (await _login(client, "sr@b.co"))["access_token"]
    ws_id = (await client.get("/api/v1/workspaces", headers=_auth(stok))).json()[0]["id"]

    invite = await client.post(
        f"/api/v1/workspaces/{ws_id}/invites",
        json={"email": "selfm@b.co", "role": "member"},
        headers=_auth(stok),
    )
    await _register(client, "selfm@b.co", "SelfM")
    mtok = (await _login(client, "selfm@b.co"))["access_token"]
    token = invite.json()["invite_url"].split("token=")[1]
    await client.post(f"/api/v1/invites/{token}/accept", headers=_auth(mtok))
    my_id = (await client.get("/api/v1/users/me", headers=_auth(mtok))).json()["id"]

    resp = await client.delete(
        f"/api/v1/workspaces/{ws_id}/members/{my_id}", headers=_auth(mtok)
    )
    assert resp.status_code == 204


async def test_benchmark_opt_in_defaults_and_persists(client: AsyncClient) -> None:
    await _register(client, "bmopt@b.co", "BmOpt")
    tok = (await _login(client, "bmopt@b.co"))["access_token"]
    ws = (await client.get("/api/v1/workspaces", headers=_auth(tok))).json()[0]
    assert ws["benchmark_opt_in"] is True

    # Owner toggles benchmark sharing off via PATCH.
    resp = await client.patch(
        f"/api/v1/workspaces/{ws['id']}",
        json={"name": ws["name"], "benchmark_opt_in": False},
        headers=_auth(tok),
    )
    assert resp.status_code == 200
    assert resp.json()["benchmark_opt_in"] is False

    # The persisted value round-trips through the listing.
    listing = (await client.get("/api/v1/workspaces", headers=_auth(tok))).json()
    assert listing[0]["benchmark_opt_in"] is False
