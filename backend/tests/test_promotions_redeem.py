"""Tests for the customer promo-code redeem endpoint (issue #99).

``POST /api/v1/promotions/redeem`` is gated by the normal verified-user auth
(the ``client`` fixture is authenticated as ``test_user``), unlike the
internal ``/codes`` endpoints. Codes are seeded directly via the ORM on the
shared ``db_session``; the endpoint resolves the caller's subscription on that
same session. No Stripe is involved — the effects tested here are purely local.
"""

from datetime import datetime, timedelta

from app.domains.billing import plans
from app.domains.billing.service import SubscriptionService
from app.domains.promotions.models import PromoCode, PromoCodeRedemption

REDEEM = "/api/v1/promotions/redeem"
SUBSCRIPTION = "/api/v1/subscription"


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


def _subscription(db_session, user_id):
    return SubscriptionService(db_session).get_for_user(user_id)


# --- Validation / rejection paths -----------------------------------------


def test_unknown_code_returns_404(client):
    resp = client.post(REDEEM, json={"code": "NOPE"})
    assert resp.status_code == 404


def test_empty_code_returns_422(client):
    resp = client.post(REDEEM, json={"code": "   "})
    assert resp.status_code == 422


def test_inactive_code_returns_400(client, db_session):
    _make_code(db_session, code="OFF", is_active=False)
    resp = client.post(REDEEM, json={"code": "OFF"})
    assert resp.status_code == 400


def test_expired_code_returns_400(client, db_session):
    _make_code(
        db_session,
        code="OLD",
        expires_at=datetime.utcnow() - timedelta(days=1),
    )
    resp = client.post(REDEEM, json={"code": "OLD"})
    assert resp.status_code == 400


def test_cap_reached_returns_400(client, db_session):
    _make_code(db_session, code="FULL", max_uses=1, used_count=1)
    resp = client.post(REDEEM, json={"code": "FULL"})
    assert resp.status_code == 400
    assert "limit" in resp.json()["detail"].lower()


def test_target_plan_mismatch_returns_400(client, db_session, test_user):
    # The seeded user is on the trial plan; a pro-only code must be rejected.
    _make_code(db_session, code="PROONLY", target_plan="pro")
    resp = client.post(REDEEM, json={"code": "PROONLY"})
    assert resp.status_code == 400
    assert "pro" in resp.json()["detail"].lower()


def test_target_plan_match_succeeds(client, db_session, test_user):
    sub = _subscription(db_session, test_user.id)
    sub.plan = plans.PLAN_PRO
    sub.status = plans.STATUS_ACTIVE
    sub.monthly_lead_quota = plans.PRO.monthly_lead_quota
    db_session.commit()

    _make_code(db_session, code="PROONLY", target_plan="pro")
    resp = client.post(REDEEM, json={"code": "PROONLY"})
    assert resp.status_code == 200
    assert resp.json()["plan"] == plans.PLAN_PRO


def test_duplicate_redemption_returns_409(client, db_session):
    _make_code(db_session, code="ONCE", max_uses=2)
    first = client.post(REDEEM, json={"code": "ONCE"})
    assert first.status_code == 200
    second = client.post(REDEEM, json={"code": "ONCE"})
    assert second.status_code == 409


# --- Happy paths per discount_type ----------------------------------------


def test_redeem_creates_one_row_and_increments_used_count(client, db_session):
    promo = _make_code(db_session, code="COUNT")
    resp = client.post(REDEEM, json={"code": "count"})  # case-insensitive
    assert resp.status_code == 200

    db_session.refresh(promo)
    assert promo.used_count == 1
    rows = (
        db_session.query(PromoCodeRedemption)
        .filter_by(promo_code_id=promo.id)
        .all()
    )
    assert len(rows) == 1


def test_percentage_changes_neither_plan_nor_quota(client, db_session, test_user):
    sub = _subscription(db_session, test_user.id)
    plan_before, quota_before = sub.plan, sub.monthly_lead_quota

    _make_code(db_session, code="PCT", discount_type="percentage", value=25)
    resp = client.post(REDEEM, json={"code": "PCT"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount_type"] == "percentage"
    assert body["comp_until"] is None
    assert body["comp_lifetime"] is False

    db_session.refresh(sub)
    assert sub.plan == plan_before
    assert sub.monthly_lead_quota == quota_before
    assert sub.comp_until is None
    assert sub.comp_lifetime is False


def test_fixed_amount_changes_neither_plan_nor_quota(client, db_session, test_user):
    sub = _subscription(db_session, test_user.id)
    plan_before, quota_before = sub.plan, sub.monthly_lead_quota

    _make_code(db_session, code="EUR5", discount_type="fixed_amount", value=5)
    resp = client.post(REDEEM, json={"code": "EUR5"})
    assert resp.status_code == 200

    db_session.refresh(sub)
    assert sub.plan == plan_before
    assert sub.monthly_lead_quota == quota_before
    assert sub.comp_lifetime is False


def test_free_months_sets_comp_until_and_plan(client, db_session, test_user):
    sub = _subscription(db_session, test_user.id)
    period_end = sub.period_end  # trial period end (~15 days out)

    _make_code(db_session, code="FREE3", discount_type="free_months", value=3)
    resp = client.post(REDEEM, json={"code": "FREE3"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount_type"] == "free_months"
    # No target_plan and a trial user → resolves to the Basic default.
    assert body["plan"] == plans.PLAN_BASIC
    assert body["comp_lifetime"] is False
    assert body["comp_until"] is not None

    db_session.refresh(sub)
    assert sub.plan == plans.PLAN_BASIC
    assert sub.monthly_lead_quota == plans.BASIC.monthly_lead_quota
    assert sub.status == plans.STATUS_ACTIVE
    assert sub.trial_ends_at is None
    # comp_until is ~3 months past the (max of now and) period end.
    assert sub.comp_until > period_end + timedelta(days=80)
    assert sub.comp_until < period_end + timedelta(days=100)


def test_free_months_resolves_current_paid_plan(client, db_session, test_user):
    sub = _subscription(db_session, test_user.id)
    sub.plan = plans.PLAN_PRO
    sub.status = plans.STATUS_ACTIVE
    sub.monthly_lead_quota = plans.PRO.monthly_lead_quota
    db_session.commit()

    _make_code(db_session, code="FREE1", discount_type="free_months", value=1)
    resp = client.post(REDEEM, json={"code": "FREE1"})
    assert resp.status_code == 200
    assert resp.json()["plan"] == plans.PLAN_PRO

    db_session.refresh(sub)
    assert sub.plan == plans.PLAN_PRO
    assert sub.monthly_lead_quota == plans.PRO.monthly_lead_quota


def test_lifetime_free_sets_comp_lifetime(client, db_session, test_user):
    _make_code(db_session, code="FOREVER", discount_type="lifetime_free", value=None)
    resp = client.post(REDEEM, json={"code": "FOREVER"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount_type"] == "lifetime_free"
    assert body["comp_lifetime"] is True
    assert body["plan"] == plans.PLAN_BASIC  # trial user, no target → Basic

    sub = _subscription(db_session, test_user.id)
    db_session.refresh(sub)
    assert sub.comp_lifetime is True
    assert sub.status == plans.STATUS_ACTIVE
    assert sub.trial_ends_at is None


# --- Comped users are not read-only past the trial window -----------------


def test_comped_user_not_read_only_past_trial(client, db_session, test_user):
    """A lifetime-comped user is never read-only from trial expiry."""
    _make_code(db_session, code="FOREVER", discount_type="lifetime_free", value=None)
    assert client.post(REDEEM, json={"code": "FOREVER"}).status_code == 200

    # Force the trial window into the past; the comp must still keep the
    # account writable (quota not exhausted).
    sub = _subscription(db_session, test_user.id)
    sub.trial_ends_at = datetime.utcnow() - timedelta(days=1)
    sub.period_end = sub.trial_ends_at
    db_session.commit()

    body = client.get(SUBSCRIPTION).json()
    assert body["plan"] == plans.PLAN_BASIC
    assert body["read_only"] is False


def test_free_months_comp_not_read_only_past_trial(client, db_session, test_user):
    _make_code(db_session, code="FREE6", discount_type="free_months", value=6)
    assert client.post(REDEEM, json={"code": "FREE6"}).status_code == 200

    sub = _subscription(db_session, test_user.id)
    sub.trial_ends_at = datetime.utcnow() - timedelta(days=1)
    db_session.commit()

    body = client.get(SUBSCRIPTION).json()
    assert body["read_only"] is False
