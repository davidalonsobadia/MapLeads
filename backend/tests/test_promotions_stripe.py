"""Tests for mirroring a redeemed promo code into Stripe (issue #103).

Redemption creates a Stripe ``Coupon`` from the ``PromoCode`` and, for a user
on a live paid subscription, applies it via ``Subscription.modify``. A trial
user (no Stripe subscription) only gets the coupon stored on the redemption;
their next ``create_checkout_session`` carries it in ``discounts``.

No real Stripe calls are made: the ``stripe`` SDK is monkeypatched and the
``settings`` singleton is patched with placeholder credentials, mirroring
``test_billing_stripe.py``. The ``client`` fixture is authenticated as
``test_user``; codes are seeded directly via the ORM on the shared
``db_session``.
"""

import stripe

from app.core.config import settings
from app.domains.billing import plans
from app.domains.billing.service import SubscriptionService
from app.domains.promotions.models import PromoCode, PromoCodeRedemption

REDEEM = "/api/v1/promotions/redeem"
CHECKOUT = "/api/v1/billing/checkout-session"


def _configure_stripe(monkeypatch):
    """Set placeholder Stripe credentials and price ids on the settings singleton."""
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_123")
    monkeypatch.setattr(settings, "STRIPE_PRICE_BASIC", "price_basic")
    monkeypatch.setattr(settings, "STRIPE_PRICE_PRO", "price_pro")
    monkeypatch.setattr(settings, "STRIPE_PRICE_ENTERPRISE", "price_enterprise")


def _subscription(db_session, user_id):
    return SubscriptionService(db_session).get_for_user(user_id)


def _make_code(db_session, code="PROMO", **overrides) -> PromoCode:
    defaults = dict(
        code=code,
        discount_type="percentage",
        value=10,
        target_plan=None,
        max_uses=100,
        used_count=0,
        is_active=True,
    )
    defaults.update(overrides)
    promo = PromoCode(**defaults)
    db_session.add(promo)
    db_session.commit()
    db_session.refresh(promo)
    return promo


def _patch_stripe(monkeypatch, captured):
    """Monkeypatch the Stripe SDK calls used by the redemption flow.

    Records call kwargs into ``captured`` and returns fake ids so the caller
    can assert the mapping and the paid-vs-trial branch.
    """

    def fake_coupon_create(**kwargs):
        captured["coupon_kwargs"] = kwargs
        return {"id": "coupon_new"}

    def fake_sub_modify(sub_id, **kwargs):
        captured["modify_id"] = sub_id
        captured["modify_kwargs"] = kwargs
        return {"id": sub_id}

    def fake_session_create(**kwargs):
        captured["session_kwargs"] = kwargs
        return {"url": "https://checkout.stripe.com/pay/cs_test_123"}

    def fake_customer_create(**kwargs):
        return {"id": "cus_new"}

    monkeypatch.setattr(stripe.Coupon, "create", fake_coupon_create)
    monkeypatch.setattr(stripe.Subscription, "modify", fake_sub_modify)
    monkeypatch.setattr(stripe.checkout.Session, "create", fake_session_create)
    monkeypatch.setattr(stripe.Customer, "create", fake_customer_create)


# --- Coupon mapping per discount_type --------------------------------------


def test_percentage_creates_percent_off_coupon(client, db_session, monkeypatch):
    _configure_stripe(monkeypatch)
    captured = {}
    _patch_stripe(monkeypatch, captured)

    _make_code(db_session, code="PCT", discount_type="percentage", value=25)
    resp = client.post(REDEEM, json={"code": "PCT"})
    assert resp.status_code == 200

    assert captured["coupon_kwargs"] == {"percent_off": 25, "duration": "forever"}


def test_fixed_amount_creates_amount_off_coupon(client, db_session, monkeypatch):
    _configure_stripe(monkeypatch)
    captured = {}
    _patch_stripe(monkeypatch, captured)

    _make_code(db_session, code="EUR5", discount_type="fixed_amount", value=5)
    resp = client.post(REDEEM, json={"code": "EUR5"})
    assert resp.status_code == 200

    # value is euros; Stripe amount_off is in cents.
    assert captured["coupon_kwargs"] == {
        "amount_off": 500,
        "currency": "eur",
        "duration": "forever",
    }


def test_free_months_creates_repeating_coupon(client, db_session, test_user, monkeypatch):
    _configure_stripe(monkeypatch)
    captured = {}
    _patch_stripe(monkeypatch, captured)

    # Put the user on a live paid subscription so the coupon is also applied.
    sub = _subscription(db_session, test_user.id)
    sub.stripe_subscription_id = "sub_live"
    db_session.commit()

    promo = _make_code(db_session, code="FREE3", discount_type="free_months", value=3)
    resp = client.post(REDEEM, json={"code": "FREE3"})
    assert resp.status_code == 200

    assert captured["coupon_kwargs"] == {
        "percent_off": 100,
        "duration": "repeating",
        "duration_in_months": 3,
    }
    # A paid subscription has the coupon applied and the id stored.
    assert captured["modify_id"] == "sub_live"
    assert captured["modify_kwargs"] == {"discounts": [{"coupon": "coupon_new"}]}

    redemption = (
        db_session.query(PromoCodeRedemption)
        .filter_by(promo_code_id=promo.id, user_id=test_user.id)
        .one()
    )
    assert redemption.stripe_coupon_id == "coupon_new"


def test_lifetime_free_creates_forever_coupon(client, db_session, test_user, monkeypatch):
    _configure_stripe(monkeypatch)
    captured = {}
    _patch_stripe(monkeypatch, captured)

    sub = _subscription(db_session, test_user.id)
    sub.stripe_subscription_id = "sub_live"
    db_session.commit()

    _make_code(db_session, code="FOREVER", discount_type="lifetime_free", value=None)
    resp = client.post(REDEEM, json={"code": "FOREVER"})
    assert resp.status_code == 200

    assert captured["coupon_kwargs"] == {"percent_off": 100, "duration": "forever"}
    assert captured["modify_kwargs"] == {"discounts": [{"coupon": "coupon_new"}]}


# --- Paid vs trial branch --------------------------------------------------


def test_trial_user_stores_coupon_without_modifying_subscription(
    client, db_session, test_user, monkeypatch
):
    """A trial user (no Stripe subscription) gets the coupon stored but not
    applied — ``Subscription.modify`` must not be called."""
    _configure_stripe(monkeypatch)
    captured = {}
    _patch_stripe(monkeypatch, captured)

    promo = _make_code(db_session, code="PCT", discount_type="percentage", value=15)
    resp = client.post(REDEEM, json={"code": "PCT"})
    assert resp.status_code == 200

    assert "modify_id" not in captured  # no Subscription.modify for a trial user

    redemption = (
        db_session.query(PromoCodeRedemption)
        .filter_by(promo_code_id=promo.id, user_id=test_user.id)
        .one()
    )
    assert redemption.stripe_coupon_id == "coupon_new"


def test_trial_redeemer_checkout_carries_coupon(
    client, db_session, test_user, monkeypatch
):
    """A trial user's granted coupon is passed into their first checkout."""
    _configure_stripe(monkeypatch)
    captured = {}
    _patch_stripe(monkeypatch, captured)

    _make_code(db_session, code="PCT", discount_type="percentage", value=15)
    assert client.post(REDEEM, json={"code": "PCT"}).status_code == 200

    resp = client.post(CHECKOUT, json={"plan": plans.PLAN_PRO})
    assert resp.status_code == 200
    assert captured["session_kwargs"]["discounts"] == [{"coupon": "coupon_new"}]


def test_checkout_without_pending_coupon_omits_discounts(
    client, db_session, test_user, monkeypatch
):
    """A checkout with no redeemed coupon does not pass ``discounts``."""
    _configure_stripe(monkeypatch)
    captured = {}
    _patch_stripe(monkeypatch, captured)

    resp = client.post(CHECKOUT, json={"plan": plans.PLAN_PRO})
    assert resp.status_code == 200
    assert "discounts" not in captured["session_kwargs"]


def test_paid_user_checkout_does_not_reapply_coupon(
    client, db_session, test_user, monkeypatch
):
    """Once a user has a live paid subscription, a stored coupon is not carried
    into a further checkout (guard against double-application)."""
    _configure_stripe(monkeypatch)
    captured = {}
    _patch_stripe(monkeypatch, captured)

    sub = _subscription(db_session, test_user.id)
    sub.stripe_subscription_id = "sub_live"
    db_session.commit()

    _make_code(db_session, code="PCT", discount_type="percentage", value=15)
    assert client.post(REDEEM, json={"code": "PCT"}).status_code == 200

    resp = client.post(CHECKOUT, json={"plan": plans.PLAN_PRO})
    assert resp.status_code == 200
    assert "discounts" not in captured["session_kwargs"]


# --- Stripe unconfigured ---------------------------------------------------


def test_redeem_succeeds_with_stripe_unconfigured(client, db_session, test_user):
    """With Stripe unset, redeem still applies local effects and does not crash."""
    # Do not configure Stripe: STRIPE_SECRET_KEY is empty in the test env.
    _make_code(db_session, code="FREE2", discount_type="free_months", value=2)
    resp = client.post(REDEEM, json={"code": "FREE2"})
    assert resp.status_code == 200
    assert resp.json()["comp_until"] is not None

    redemption = (
        db_session.query(PromoCodeRedemption)
        .filter_by(user_id=test_user.id)
        .one()
    )
    assert redemption.stripe_coupon_id is None
