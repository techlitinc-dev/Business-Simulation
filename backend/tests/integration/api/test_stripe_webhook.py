"""Integration tests for the Stripe webhook endpoint (T40)."""

import json

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def _stripe_env(monkeypatch) -> None:
    """Point settings at a Stripe-test config for every test in this file."""
    from app.core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("STRIPE_PRICE_PRO_MONTHLY", "price_pro")
    monkeypatch.setenv("STRIPE_PRICE_ENTERPRISE_MONTHLY", "price_ent")
    yield
    get_settings.cache_clear()  # type: ignore[attr-defined]


_SIGNED_EVENT = {
    "id": "evt_sub_1",
    "type": "customer.subscription.updated",
    "data": {
        "object": {
            "id": "sub_1",
            "customer": "cus_123",
            "status": "active",
            "current_period_end": 1800000000,
            "items": {"data": [{"price": {"id": "price_pro"}}]},
        }
    },
}


async def _setup_workspace_with_customer(client: AsyncClient, email: str) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Wh", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    ws = (await client.get(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
    )).json()[0]

    # Simulate an existing Stripe customer via direct DB update through the app.
    import uuid

    from app.db.session import async_session_factory
    from app.models.workspace import Workspace

    async with async_session_factory() as session:
        workspace = await session.get(Workspace, uuid.UUID(ws["id"]))
        workspace.stripe_customer_id = "cus_123"
        await session.commit()

    return {
        "token": token,
        "workspace_id": ws["id"],
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws["id"]},
    }


async def _webhook_request(client: AsyncClient, payload: dict, signature: str):
    import time

    import stripe

    payload_bytes = json.dumps(payload).encode()
    if signature == "valid":
        timestamp = int(time.time())
        signed_payload = f"{timestamp}.{payload_bytes.decode()}"
        sig = stripe.WebhookSignature._compute_signature(
            signed_payload, "whsec_test"
        )
        header = f"t={timestamp},v1={sig}"
    else:
        header = "t=123,v1=deadbeef"
    return await client.post(
        "/api/v1/webhooks/stripe",
        content=payload_bytes,
        headers={"Stripe-Signature": header, "Content-Type": "application/json"},
    )


async def test_webhook_invalid_signature_400(client: AsyncClient) -> None:
    resp = await _webhook_request(client, _SIGNED_EVENT, "bad")
    assert resp.status_code == 400


async def test_webhook_missing_signature_400(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/webhooks/stripe",
        content=json.dumps(_SIGNED_EVENT),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


async def test_webhook_valid_event_upserts_subscription(
    client: AsyncClient,
) -> None:
    account = await _setup_workspace_with_customer(client, "wh1@b.co")

    resp = await _webhook_request(client, _SIGNED_EVENT, "valid")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("created") is True or body.get("updated") is True

    sub_resp = await client.get(
        "/api/v1/billing/subscription",
        headers=account["headers"],
    )
    assert sub_resp.status_code == 200
    assert sub_resp.json()["tier"] == "pro"
    assert sub_resp.json()["status"] == "active"


async def test_webhook_redelivery_is_idempotent(
    client: AsyncClient,
) -> None:
    account = await _setup_workspace_with_customer(client, "wh2@b.co")

    first = await _webhook_request(client, _SIGNED_EVENT, "valid")
    assert first.status_code == 200

    # Re-deliver the SAME event id with a modified payload — must be a no-op.
    changed = json.loads(json.dumps(_SIGNED_EVENT))
    changed["data"]["object"]["current_period_end"] = 1900000000

    second = await _webhook_request(client, changed, "valid")
    assert second.status_code == 200
    assert second.json()["duplicate"] is True

    sub_resp = await client.get(
        "/api/v1/billing/subscription",
        headers=account["headers"],
    )
    assert sub_resp.json()["tier"] == "pro"
