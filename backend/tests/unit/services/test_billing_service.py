"""Unit tests for billing_service (T40) with the Stripe SDK mocked."""

import pytest
from app.core.exceptions import DomainError
from app.db.base import Base
from app.models.billing import Subscription
from app.models.workspace import Workspace
from app.services import billing_service
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_SETTINGS = type("S", (), {
    "stripe_secret_key": "sk_test",
    "frontend_url": "http://localhost:5173",
    "stripe_price_pro_monthly": "price_pro",
    "stripe_price_enterprise_monthly": "price_ent",
})()


class FakeCustomer(dict):
    def __init__(self) -> None:
        super().__init__({"id": "cus_123"})


class FakeCheckoutSession(dict):
    def __init__(self) -> None:
        super().__init__({"url": "https://checkout.stripe.com/c/pay_123"})


class FakePortalSession(dict):
    def __init__(self) -> None:
        super().__init__({"url": "https://billing.stripe.com/p/session_123"})


@pytest.fixture
async def db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def _stripe_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.get_settings", lambda: _SETTINGS)


@pytest.fixture
def _mock_stripe(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCustomerCls:
        @classmethod
        def create(cls, **kw):  # noqa: N805
            return FakeCustomer()

    class FakeCheckoutSessionCls:
        @classmethod
        def create(cls, **kw):  # noqa: N805
            return FakeCheckoutSession()

    class Checkout:
        Session = FakeCheckoutSessionCls

    class FakePortalSessionCls:
        @classmethod
        def create(cls, **kw):  # noqa: N805
            return FakePortalSession()

    class Portal:
        Session = FakePortalSessionCls

    class FakeStripe:
        Customer = FakeCustomerCls
        checkout = Checkout
        billing_portal = Portal

    monkeypatch.setattr(
        "app.services.billing_service._stripe", lambda: FakeStripe()
    )


async def test_create_checkout_session_creates_customer_and_url(
    _mock_stripe: None, db: AsyncSession
) -> None:
    workspace = Workspace(name="Acme", slug="acme-1234", plan_tier="free")
    db.add(workspace)
    await db.commit()

    url = await billing_service.create_checkout_session(
        db, workspace=workspace, tier="pro"
    )
    assert url == "https://checkout.stripe.com/c/pay_123"
    assert workspace.stripe_customer_id == "cus_123"


async def test_create_checkout_session_free_tier_rejected(
    _mock_stripe: None, db: AsyncSession
) -> None:
    workspace = Workspace(name="Acme", slug="acme-1234", plan_tier="free")
    db.add(workspace)
    await db.commit()

    with pytest.raises(DomainError) as exc:
        await billing_service.create_checkout_session(
            db, workspace=workspace, tier="free"
        )
    assert exc.value.status_code == 422


async def test_create_portal_session_404_without_customer(
    db: AsyncSession,
) -> None:
    workspace = Workspace(name="Acme", slug="acme-1234", plan_tier="free")
    db.add(workspace)
    await db.commit()

    with pytest.raises(DomainError) as exc:
        await billing_service.create_portal_session(
            db, workspace=workspace
        )
    assert exc.value.status_code == 404


async def test_create_portal_session_returns_url(
    _mock_stripe: None, db: AsyncSession
) -> None:
    workspace = Workspace(
        name="Acme", slug="acme-1234", plan_tier="free", stripe_customer_id="cus_123"
    )
    db.add(workspace)
    await db.commit()

    url = await billing_service.create_portal_session(
        db, workspace=workspace
    )
    assert url == "https://billing.stripe.com/p/session_123"


async def test_handle_webhook_event_upserts_subscription(
    db: AsyncSession,
) -> None:
    workspace = Workspace(
        name="Acme", slug="acme-1234", plan_tier="free", stripe_customer_id="cus_123"
    )
    db.add(workspace)
    await db.commit()

    event = {
        "id": "evt_1",
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

    result = await billing_service.handle_webhook_event(db, event)
    assert result.get("created") is True or result.get("updated") is True

    sub = await db.scalar(
        select(Subscription).where(Subscription.stripe_subscription_id == "sub_1")
    )
    assert sub is not None
    assert sub.tier == "pro"
    assert sub.status == "active"
    assert sub.workspace_id == workspace.id
    assert workspace.plan_tier == "pro"


async def test_handle_webhook_unknown_customer_ignored(
    db: AsyncSession,
) -> None:
    event = {
        "id": "evt_9",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_9",
                "customer": "cus_unknown",
                "status": "active",
                "items": {"data": [{"price": {"id": "price_pro"}}]},
            }
        },
    }
    result = await billing_service.handle_webhook_event(db, event)
    assert result.get("ignored") == "unknown_customer"

