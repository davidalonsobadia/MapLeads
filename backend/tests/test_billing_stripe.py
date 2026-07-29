"""Tests for the Stripe billing integration: Checkout, Billing Portal and the
webhook that syncs the local ``Subscription`` with Stripe.

No real Stripe calls are made — the ``stripe`` SDK is monkeypatched and the
``settings`` singleton is patched with placeholder credentials. The ``client``
fixture is authenticated as ``test_user`` (see ``conftest.py``); the API-key
middleware is disabled under ``TESTING=1``, so the webhook can be posted
directly.
"""

from datetime import datetime, timedelta

import stripe

from app.core.config import settings
from app.core.middleware.api_key import EXEMPT_PATHS
from app.domains.billing import plans
from app.domains.billing.service import SubscriptionService

CHECKOUT = "/api/v1/billing/checkout-session"
PORTAL = "/api/v1/billing/portal-session"
WEBHOOK = "/api/v1/billing/webhook"


def _configure_stripe(monkeypatch):
    """Set placeholder Stripe credentials and price ids on the settings singleton."""
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_123")
    monkeypatch.setattr(settings, "STRIPE_PRICE_BASIC", "price_basic")
    monkeypatch.setattr(settings, "STRIPE_PRICE_PRO", "price_pro")
    monkeypatch.setattr(settings, "STRIPE_PRICE_ENTERPRISE", "price_enterprise")


def _get_subscription(db_session, user_id):
    return SubscriptionService(db_session).get_for_user(user_id)


def _stripe_subscription(*, user_id, period_start, period_end, price_id="price_pro",
                         status="active", customer="cus_1", sub_id="sub_1"):
    """A minimal fake of a retrieved Stripe subscription object (a plain dict).

    Matches the current Stripe API shape: ``current_period_start``/``_end``
    live on the subscription *item*, not on the subscription itself (Stripe
    moved them so each item can bill on its own cycle).
    """
    return {
        "id": sub_id,
        "customer": customer,
        "status": status,
        "items": {
            "data": [
                {
                    "price": {"id": price_id},
                    "current_period_start": int(period_start.timestamp()),
                    "current_period_end": int(period_end.timestamp()),
                }
            ]
        },
        "metadata": {"user_id": str(user_id)},
    }


# --- Checkout & Portal -----------------------------------------------------


def test_checkout_session_returns_url(client, test_user, monkeypatch):
    _configure_stripe(monkeypatch)
    captured = {}

    def fake_customer_create(**kwargs):
        captured["customer_kwargs"] = kwargs
        return {"id": "cus_new"}

    def fake_session_create(**kwargs):
        captured["session_kwargs"] = kwargs
        return {"url": "https://checkout.stripe.com/pay/cs_test_123"}

    monkeypatch.setattr(stripe.Customer, "create", fake_customer_create)
    monkeypatch.setattr(stripe.checkout.Session, "create", fake_session_create)

    response = client.post(CHECKOUT, json={"plan": plans.PLAN_PRO})
    assert response.status_code == 200
    assert response.json()["url"].startswith("https://checkout.stripe.com/")

    # A customer was created and reused, and the target price was passed through.
    assert captured["session_kwargs"]["customer"] == "cus_new"
    assert captured["session_kwargs"]["line_items"] == [
        {"price": "price_pro", "quantity": 1}
    ]
    assert captured["session_kwargs"]["mode"] == "subscription"


def test_checkout_session_rejects_invalid_plan(client, monkeypatch):
    _configure_stripe(monkeypatch)
    # "trial" is not a purchasable plan; the field validator rejects it as 422.
    response = client.post(CHECKOUT, json={"plan": plans.PLAN_TRIAL})
    assert response.status_code == 422


def test_checkout_session_unconfigured_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")
    response = client.post(CHECKOUT, json={"plan": plans.PLAN_PRO})
    assert response.status_code == 503


def test_portal_session_returns_url(client, test_user, db_session, monkeypatch):
    _configure_stripe(monkeypatch)
    sub = _get_subscription(db_session, test_user.id)
    sub.stripe_customer_id = "cus_existing"
    db_session.commit()

    def fake_portal_create(**kwargs):
        assert kwargs["customer"] == "cus_existing"
        return {"url": "https://billing.stripe.com/p/session_123"}

    monkeypatch.setattr(stripe.billing_portal.Session, "create", fake_portal_create)

    response = client.post(PORTAL)
    assert response.status_code == 200
    assert response.json()["url"].startswith("https://billing.stripe.com/")


def test_portal_session_without_customer_returns_400(client, monkeypatch):
    _configure_stripe(monkeypatch)
    response = client.post(PORTAL)
    assert response.status_code == 400


# --- Webhook ---------------------------------------------------------------


def test_webhook_path_is_exempt_from_api_key_middleware():
    assert WEBHOOK in EXEMPT_PATHS


def test_webhook_unconfigured_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    response = client.post(WEBHOOK, content=b"{}", headers={"stripe-signature": "x"})
    assert response.status_code == 503


def test_webhook_rejects_bad_signature(client, monkeypatch):
    _configure_stripe(monkeypatch)

    def fake_construct_event(payload, signature, secret):
        raise stripe.error.SignatureVerificationError("bad", signature)

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)

    response = client.post(
        WEBHOOK, content=b"{}", headers={"stripe-signature": "bad"}
    )
    assert response.status_code == 400


def test_webhook_checkout_completed_upgrades_subscription(
    client, test_user, db_session, monkeypatch
):
    """A valid checkout.session.completed upgrades the trial to a paid plan,
    clears the trial, and resets usage for the new billing period."""
    _configure_stripe(monkeypatch)

    sub = _get_subscription(db_session, test_user.id)
    # Simulate leads saved during the trial: these must not be pre-consumed
    # from the new paid quota.
    sub.leads_used_this_period = 150
    db_session.commit()

    now = datetime.utcnow()
    period_start = now
    period_end = now + timedelta(days=30)
    stripe_sub = _stripe_subscription(
        user_id=test_user.id,
        period_start=period_start,
        period_end=period_end,
        price_id="price_pro",
        customer="cus_1",
    )

    def fake_construct_event(payload, signature, secret):
        return {
            "type": "checkout.session.completed",
            "data": {"object": {"customer": "cus_1", "subscription": "sub_1"}},
        }

    def fake_sub_retrieve(sub_id, **kwargs):
        assert sub_id == "sub_1"
        return stripe_sub

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)
    monkeypatch.setattr(stripe.Subscription, "retrieve", fake_sub_retrieve)

    response = client.post(
        WEBHOOK, content=b"{}", headers={"stripe-signature": "ok"}
    )
    assert response.status_code == 200
    assert response.json() == {"received": True}

    db_session.refresh(sub)
    assert sub.plan == plans.PLAN_PRO
    assert sub.status == plans.STATUS_ACTIVE
    assert sub.monthly_lead_quota == plans.PRO.monthly_lead_quota
    assert sub.read_only is False
    assert sub.trial_ends_at is None
    assert sub.stripe_customer_id == "cus_1"
    assert sub.stripe_subscription_id == "sub_1"
    # The new billing period starts with a clean usage counter.
    assert sub.leads_used_this_period == 0


def test_webhook_subscription_updated_renewal_resets_usage(
    client, test_user, db_session, monkeypatch
):
    """A renewal (new period on customer.subscription.updated) resets usage and
    unblocks a previously quota-locked account."""
    _configure_stripe(monkeypatch)

    sub = _get_subscription(db_session, test_user.id)
    sub.plan = plans.PLAN_PRO
    sub.status = plans.STATUS_ACTIVE
    sub.monthly_lead_quota = plans.PRO.monthly_lead_quota
    sub.leads_used_this_period = plans.PRO.monthly_lead_quota  # quota exhausted
    sub.read_only = True
    sub.stripe_customer_id = "cus_1"
    sub.trial_ends_at = None
    old_end = datetime.utcnow()
    sub.period_start = old_end - timedelta(days=30)
    sub.period_end = old_end
    db_session.commit()

    new_start = old_end
    new_end = old_end + timedelta(days=30)
    stripe_sub = _stripe_subscription(
        user_id=test_user.id,
        period_start=new_start,
        period_end=new_end,
        price_id="price_pro",
        customer="cus_1",
    )

    def fake_construct_event(payload, signature, secret):
        return {
            "type": "customer.subscription.updated",
            "data": {"object": stripe_sub},
        }

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)

    response = client.post(
        WEBHOOK, content=b"{}", headers={"stripe-signature": "ok"}
    )
    assert response.status_code == 200

    db_session.refresh(sub)
    assert sub.leads_used_this_period == 0
    assert sub.read_only is False


def test_webhook_subscription_updated_same_period_preserves_usage(
    client, test_user, db_session, monkeypatch
):
    """A mid-period update (same period, e.g. payment-method change) preserves
    usage and keeps a quota-exhausted account read-only."""
    _configure_stripe(monkeypatch)

    start = datetime.utcnow() - timedelta(days=5)
    end = datetime.utcnow() + timedelta(days=25)

    sub = _get_subscription(db_session, test_user.id)
    sub.plan = plans.PLAN_PRO
    sub.status = plans.STATUS_ACTIVE
    sub.monthly_lead_quota = plans.PRO.monthly_lead_quota
    sub.leads_used_this_period = plans.PRO.monthly_lead_quota  # quota exhausted
    sub.read_only = True
    sub.stripe_customer_id = "cus_1"
    sub.trial_ends_at = None
    # Match the timestamps the event will carry so the period is unchanged.
    stripe_sub = _stripe_subscription(
        user_id=test_user.id,
        period_start=start,
        period_end=end,
        price_id="price_pro",
        customer="cus_1",
    )
    item = stripe_sub["items"]["data"][0]
    sub.period_start = datetime.utcfromtimestamp(item["current_period_start"])
    sub.period_end = datetime.utcfromtimestamp(item["current_period_end"])
    db_session.commit()

    def fake_construct_event(payload, signature, secret):
        return {
            "type": "customer.subscription.updated",
            "data": {"object": stripe_sub},
        }

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)

    response = client.post(
        WEBHOOK, content=b"{}", headers={"stripe-signature": "ok"}
    )
    assert response.status_code == 200

    db_session.refresh(sub)
    # Usage preserved within the same period and the account stays read-only
    # because the quota is still exhausted.
    assert sub.leads_used_this_period == plans.PRO.monthly_lead_quota


def test_webhook_subscription_updated_legacy_top_level_period_fields(
    client, test_user, db_session, monkeypatch
):
    """Older Stripe API versions report current_period_start/_end on the
    subscription itself rather than on each item; the fallback must still work."""
    _configure_stripe(monkeypatch)
    _get_subscription(db_session, test_user.id)  # provision the trial subscription

    now = datetime.utcnow()
    period_start = now
    period_end = now + timedelta(days=30)
    stripe_sub = {
        "id": "sub_legacy",
        "customer": "cus_1",
        "status": "active",
        "current_period_start": int(period_start.timestamp()),
        "current_period_end": int(period_end.timestamp()),
        "items": {"data": [{"price": {"id": "price_pro"}}]},
        "metadata": {"user_id": str(test_user.id)},
    }

    def fake_construct_event(payload, signature, secret):
        return {
            "type": "customer.subscription.updated",
            "data": {"object": stripe_sub},
        }

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)

    response = client.post(
        WEBHOOK, content=b"{}", headers={"stripe-signature": "ok"}
    )
    assert response.status_code == 200

    sub = _get_subscription(db_session, test_user.id)
    assert sub.plan == plans.PLAN_PRO
    assert sub.stripe_subscription_id == "sub_legacy"
    assert sub.read_only is False


def test_webhook_subscription_deleted_marks_canceled_read_only(
    client, test_user, db_session, monkeypatch
):
    _configure_stripe(monkeypatch)

    sub = _get_subscription(db_session, test_user.id)
    sub.plan = plans.PLAN_PRO
    sub.status = plans.STATUS_ACTIVE
    sub.stripe_customer_id = "cus_1"
    sub.read_only = False
    db_session.commit()

    def fake_construct_event(payload, signature, secret):
        return {
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_1", "metadata": {}}},
        }

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)

    response = client.post(
        WEBHOOK, content=b"{}", headers={"stripe-signature": "ok"}
    )
    assert response.status_code == 200

    db_session.refresh(sub)
    assert sub.status == plans.STATUS_CANCELED
    assert sub.read_only is True


class _FakeStripeObject:
    """Mimics the real ``stripe`` SDK's ``StripeObject`` shape: indexable and
    recursively convertible via ``to_dict()``, but does NOT support ``.get()``.
    Every other test in this file mocks Stripe responses as plain dicts, which
    masked a real bug: production code called ``.get()`` on genuine SDK
    objects and crashed with ``AttributeError``. This fake guards against that
    regressing."""

    def __init__(self, data):
        self._data = {
            k: _FakeStripeObject(v) if isinstance(v, dict) else v
            for k, v in data.items()
        }

    def __getitem__(self, key):
        return self._data[key]

    def to_dict(self):
        return {
            k: (v.to_dict() if isinstance(v, _FakeStripeObject) else v)
            for k, v in self._data.items()
        }


def test_webhook_checkout_completed_handles_real_stripe_sdk_objects(
    client, test_user, db_session, monkeypatch
):
    """The webhook must work against real Stripe SDK response shapes, not just
    the plain-dict test doubles used elsewhere in this file."""
    _configure_stripe(monkeypatch)
    _get_subscription(db_session, test_user.id)  # provision the trial subscription

    now = datetime.utcnow()
    stripe_sub = _stripe_subscription(
        user_id=test_user.id,
        period_start=now,
        period_end=now + timedelta(days=30),
        price_id="price_pro",
        customer="cus_1",
        sub_id="sub_1",
    )

    def fake_construct_event(payload, signature, secret):
        return _FakeStripeObject(
            {
                "type": "checkout.session.completed",
                "data": {"object": {"customer": "cus_1", "subscription": "sub_1"}},
            }
        )

    def fake_sub_retrieve(sub_id, **kwargs):
        assert sub_id == "sub_1"
        return _FakeStripeObject(stripe_sub)

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)
    monkeypatch.setattr(stripe.Subscription, "retrieve", fake_sub_retrieve)

    response = client.post(
        WEBHOOK, content=b"{}", headers={"stripe-signature": "ok"}
    )
    assert response.status_code == 200

    sub = _get_subscription(db_session, test_user.id)
    assert sub.plan == plans.PLAN_PRO
    assert sub.stripe_customer_id == "cus_1"
    assert sub.stripe_subscription_id == "sub_1"


def test_webhook_ignores_unhandled_event(client, monkeypatch):
    _configure_stripe(monkeypatch)

    def fake_construct_event(payload, signature, secret):
        return {"type": "invoice.paid", "data": {"object": {}}}

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)

    response = client.post(
        WEBHOOK, content=b"{}", headers={"stripe-signature": "ok"}
    )
    assert response.status_code == 200
    assert response.json() == {"received": True}
