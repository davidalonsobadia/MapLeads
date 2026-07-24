"""Tests for the Stripe billing integration (Checkout, Billing Portal, webhook).

No real Stripe calls are made: the ``stripe`` SDK methods used by
``StripeBillingService`` are monkeypatched on the real module (so the genuine
``stripe.error.SignatureVerificationError`` type is preserved for the
signature-failure path). We assert the outgoing session-creation payloads, that a
bad webhook signature returns 400, and that a valid ``checkout.session.completed``
event upgrades the local subscription.
"""

import json

import pytest
import stripe

from app.core.config import settings
from app.domains.billing import plans
from app.domains.billing.models import Subscription
from app.domains.billing.service import SubscriptionService

CHECKOUT = "/api/v1/billing/checkout-session"
PORTAL = "/api/v1/billing/portal-session"
WEBHOOK = "/api/v1/billing/webhook"


@pytest.fixture
def stripe_config(monkeypatch):
    """Configure Stripe settings with placeholder values for the duration of a test."""
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_123", raising=False)
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_123", raising=False)
    monkeypatch.setattr(settings, "STRIPE_PRICE_BASIC", "price_basic", raising=False)
    monkeypatch.setattr(settings, "STRIPE_PRICE_PRO", "price_pro", raising=False)
    monkeypatch.setattr(
        settings, "STRIPE_PRICE_ENTERPRISE", "price_ent", raising=False
    )


def _seed_subscription(db_session, user_id) -> Subscription:
    return SubscriptionService(db_session).get_for_user(user_id)


def test_checkout_session_returns_url_and_builds_payload(
    client, test_user, stripe_config, monkeypatch
):
    """POST /billing/checkout-session creates a customer + subscription session."""
    captured = {}

    def fake_customer_create(**kwargs):
        captured["customer"] = kwargs
        return {"id": "cus_new"}

    def fake_session_create(**kwargs):
        captured["session"] = kwargs
        return {"url": "https://checkout.stripe.com/c/pay/cs_test_123"}

    monkeypatch.setattr(stripe.Customer, "create", fake_customer_create)
    monkeypatch.setattr(stripe.checkout.Session, "create", fake_session_create)

    response = client.post(CHECKOUT, json={"plan": plans.PLAN_BASIC})
    assert response.status_code == 200
    assert response.json()["url"].startswith("https://checkout.stripe.com/")

    # A Stripe customer was created for the user and reused in the session.
    assert captured["customer"]["email"] == test_user.email
    session = captured["session"]
    assert session["mode"] == "subscription"
    assert session["customer"] == "cus_new"
    assert session["client_reference_id"] == str(test_user.id)
    assert session["line_items"] == [{"price": "price_basic", "quantity": 1}]
    assert session["metadata"]["plan"] == plans.PLAN_BASIC


def test_checkout_rejects_unknown_plan(client, stripe_config, monkeypatch):
    """A non-purchasable plan is rejected before any Stripe call."""

    def boom(**kwargs):  # pragma: no cover - must never be called
        raise AssertionError("Stripe must not be called for an invalid plan")

    monkeypatch.setattr(stripe.checkout.Session, "create", boom)

    response = client.post(CHECKOUT, json={"plan": "trial"})
    assert response.status_code == 422


def test_checkout_requires_configuration(client, monkeypatch):
    """Without a secret key, checkout returns 503 rather than a broken call."""
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "", raising=False)
    response = client.post(CHECKOUT, json={"plan": plans.PLAN_BASIC})
    assert response.status_code == 503


def test_portal_session_returns_url(
    client, test_user, db_session, stripe_config, monkeypatch
):
    """POST /billing/portal-session returns a portal URL for an existing customer."""
    sub = _seed_subscription(db_session, test_user.id)
    sub.stripe_customer_id = "cus_existing"
    db_session.commit()

    captured = {}

    def fake_portal_create(**kwargs):
        captured.update(kwargs)
        return {"url": "https://billing.stripe.com/p/session_123"}

    monkeypatch.setattr(stripe.billing_portal.Session, "create", fake_portal_create)

    response = client.post(PORTAL)
    assert response.status_code == 200
    assert response.json()["url"].startswith("https://billing.stripe.com/")
    assert captured["customer"] == "cus_existing"


def test_portal_without_customer_returns_409(client, test_user, stripe_config):
    """A user who never subscribed has no billing account to manage."""
    response = client.post(PORTAL)
    assert response.status_code == 409


def test_webhook_rejects_bad_signature(client, stripe_config, monkeypatch):
    """An invalid signature is rejected with 400 and never processed."""

    def fake_construct_event(payload, sig_header, secret):
        raise stripe.error.SignatureVerificationError("bad sig", sig_header)

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)

    response = client.post(
        WEBHOOK, content=b"{}", headers={"stripe-signature": "t=1,v1=bad"}
    )
    assert response.status_code == 400


def test_webhook_checkout_completed_upgrades_subscription(
    client, test_user, db_session, stripe_config, monkeypatch
):
    """A valid checkout.session.completed event upgrades the local subscription."""
    sub = _seed_subscription(db_session, test_user.id)
    assert sub.plan == plans.PLAN_TRIAL
    assert sub.trial_ends_at is not None

    period_start = 1_700_000_000
    period_end = 1_702_592_000  # ~30 days later

    def fake_construct_event(payload, sig_header, secret):
        assert secret == "whsec_123"
        return {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_1",
                    "client_reference_id": str(test_user.id),
                    "subscription": "sub_1",
                    "metadata": {"user_id": str(test_user.id), "plan": plans.PLAN_PRO},
                }
            },
        }

    def fake_sub_retrieve(sub_id):
        assert sub_id == "sub_1"
        return {
            "id": "sub_1",
            "status": "active",
            "customer": "cus_1",
            "current_period_start": period_start,
            "current_period_end": period_end,
            "items": {"data": [{"price": {"id": "price_pro"}}]},
        }

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)
    monkeypatch.setattr(stripe.Subscription, "retrieve", fake_sub_retrieve)

    response = client.post(
        WEBHOOK,
        content=json.dumps({"stub": True}).encode(),
        headers={"stripe-signature": "t=1,v1=good"},
    )
    assert response.status_code == 200
    assert response.json() == {"received": True}

    db_session.expire_all()
    updated = (
        db_session.query(Subscription)
        .filter(Subscription.user_id == test_user.id)
        .first()
    )
    assert updated.plan == plans.PLAN_PRO
    assert updated.status == plans.STATUS_ACTIVE
    assert updated.monthly_lead_quota == plans.PRO.monthly_lead_quota
    assert updated.read_only is False
    assert updated.trial_ends_at is None
    assert updated.stripe_customer_id == "cus_1"
    assert updated.stripe_subscription_id == "sub_1"
    assert updated.period_end.year == 2023


def test_webhook_subscription_deleted_marks_read_only(
    client, test_user, db_session, stripe_config, monkeypatch
):
    """A customer.subscription.deleted event cancels the local subscription."""
    sub = _seed_subscription(db_session, test_user.id)
    sub.plan = plans.PLAN_PRO
    sub.status = plans.STATUS_ACTIVE
    sub.stripe_customer_id = "cus_del"
    db_session.commit()

    def fake_construct_event(payload, sig_header, secret):
        return {
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_del", "status": "canceled"}},
        }

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)

    response = client.post(
        WEBHOOK, content=b"{}", headers={"stripe-signature": "t=1,v1=good"}
    )
    assert response.status_code == 200

    db_session.expire_all()
    updated = (
        db_session.query(Subscription)
        .filter(Subscription.user_id == test_user.id)
        .first()
    )
    assert updated.status == plans.STATUS_CANCELED
    assert updated.read_only is True


def test_webhook_path_is_exempt_from_api_key_middleware():
    """The Stripe webhook must be reachable without an x-api-key header."""
    from app.core.middleware.api_key import EXEMPT_PATHS

    assert WEBHOOK in EXEMPT_PATHS
