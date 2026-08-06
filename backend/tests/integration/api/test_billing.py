"""Integration tests for billing endpoints (T40)."""

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


async def _register(client: AsyncClient, email: str) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Bill", "password": "password123"},
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


async def _mock_stripe(monkeypatch) -> None:
    class FakeCustomer(dict):
        def __init__(self) -> None:
            super().__init__({"id": "cus_123"})

    class FakeCheckoutSession(dict):
        def __init__(self) -> None:
            super().__init__({"url": "https://checkout.stripe.com/c/pay_123"})

    class FakePortalSession(dict):
        def __init__(self) -> None:
            super().__init__({"url": "https://billing.stripe.com/p/session_123"})

    class CustomerCls:
        @classmethod
        def create(cls, **kw):  # noqa: N805
            return FakeCustomer()

    class CheckoutSessionCls:
        @classmethod
        def create(cls, **kw):  # noqa: N805
            return FakeCheckoutSession()

    class Checkout:
        Session = CheckoutSessionCls

    class PortalSessionCls:
        @classmethod
        def create(cls, **kw):  # noqa: N805
            return FakePortalSession()

    class Portal:
        Session = PortalSessionCls

    class FakeStripe:
        Customer = CustomerCls
        checkout = Checkout
        billing_portal = Portal

    monkeypatch.setattr(
        "app.services.billing_service._stripe", lambda: FakeStripe()
    )


async def test_checkout_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/billing/checkout", json={"tier": "pro"}
    )
    assert resp.status_code == 401


async def test_checkout_creates_session_and_persists_customer(
    client: AsyncClient, monkeypatch
) -> None:
    await _mock_stripe(monkeypatch)
    account = await _register(client, "bill1@b.co")

    resp = await client.post(
        "/api/v1/billing/checkout",
        headers=account["headers"],
        json={"tier": "pro"},
    )
    assert resp.status_code == 200
    assert resp.json()["checkout_url"] == "https://checkout.stripe.com/c/pay_123"


async def test_checkout_free_tier_rejected(client: AsyncClient, monkeypatch) -> None:
    await _mock_stripe(monkeypatch)
    account = await _register(client, "bill2@b.co")

    resp = await client.post(
        "/api/v1/billing/checkout",
        headers=account["headers"],
        json={"tier": "free"},
    )
    assert resp.status_code == 422


async def test_portal_404_without_customer(client: AsyncClient, monkeypatch) -> None:
    await _mock_stripe(monkeypatch)
    account = await _register(client, "bill3@b.co")

    resp = await client.post(
        "/api/v1/billing/portal",
        headers=account["headers"],
    )
    assert resp.status_code == 404


async def test_portal_returns_url_with_customer(client: AsyncClient, monkeypatch) -> None:
    await _mock_stripe(monkeypatch)
    account = await _register(client, "bill4@b.co")

    await client.post(
        "/api/v1/billing/checkout",
        headers=account["headers"],
        json={"tier": "pro"},
    )
    resp = await client.post(
        "/api/v1/billing/portal",
        headers=account["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["portal_url"] == "https://billing.stripe.com/p/session_123"


async def test_subscription_defaults_to_free(client: AsyncClient) -> None:
    account = await _register(client, "bill5@b.co")

    resp = await client.get(
        "/api/v1/billing/subscription",
        headers=account["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "free"
    assert body["status"] == "active"
    assert body["current_period_end"] is None
