"""Tests for the billing Subscription model, plan config and trial
provisioning on registration."""

from datetime import datetime, timedelta

import pytest

from app.domains.auth import schemas
from app.domains.auth.models import User
from app.domains.auth.service import AuthService
from app.domains.billing import plans
from app.domains.billing.models import Subscription


@pytest.fixture(autouse=True)
def _no_email(monkeypatch):
    """Registration fires a Celery email task; stub it so tests don't try to
    reach the email provider."""
    monkeypatch.setattr(
        "app.domains.auth.service.send_verification_email_task.delay",
        lambda *args, **kwargs: None,
    )


def test_plan_catalog_is_centralized_and_importable():
    assert set(plans.PLANS) == {
        plans.PLAN_BASIC,
        plans.PLAN_PRO,
        plans.PLAN_ENTERPRISE,
    }
    assert plans.BASIC.monthly_lead_quota == 200
    assert plans.BASIC.max_active_projects == 1
    assert plans.PRO.monthly_lead_quota == 800
    assert plans.PRO.max_active_projects is None  # unlimited
    assert plans.ENTERPRISE.monthly_lead_quota == 2500
    assert plans.ENTERPRISE.max_active_projects is None  # unlimited


def test_register_creates_single_trial_subscription(db_session):
    before = datetime.utcnow()
    user = AuthService(db_session).register_user(
        schemas.UserRegister(
            name="New User",
            email="new@example.com",
            password="supersecret",
        )
    )
    after = datetime.utcnow()

    subs = db_session.query(Subscription).filter_by(user_id=user.id).all()
    assert len(subs) == 1  # exactly one subscription per user

    sub = subs[0]
    assert sub.plan == plans.PLAN_TRIAL
    assert sub.status == plans.STATUS_TRIALING
    assert sub.monthly_lead_quota == plans.TRIAL_LEAD_QUOTA == 200
    assert sub.leads_used_this_period == 0
    assert sub.read_only is False
    assert sub.stripe_customer_id is None
    assert sub.stripe_subscription_id is None

    # trial_ends_at is 15 days out and the period spans the trial window.
    expected_end_lo = before + timedelta(days=plans.TRIAL_PERIOD_DAYS)
    expected_end_hi = after + timedelta(days=plans.TRIAL_PERIOD_DAYS)
    assert expected_end_lo <= sub.trial_ends_at <= expected_end_hi
    assert sub.period_end == sub.trial_ends_at
    assert before <= sub.period_start <= after


def test_one_subscription_per_user_enforced(db_session):
    user = User(
        name="Owner",
        email="owner@example.com",
        hashed_password="x",
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    now = datetime.utcnow()
    db_session.add(
        Subscription(
            user_id=user.id,
            plan=plans.PLAN_TRIAL,
            status=plans.STATUS_TRIALING,
            monthly_lead_quota=plans.TRIAL_LEAD_QUOTA,
            period_start=now,
            period_end=now + timedelta(days=plans.TRIAL_PERIOD_DAYS),
            trial_ends_at=now + timedelta(days=plans.TRIAL_PERIOD_DAYS),
        )
    )
    db_session.commit()

    # A second subscription for the same user violates the unique constraint.
    db_session.add(
        Subscription(
            user_id=user.id,
            plan=plans.PLAN_BASIC,
            status=plans.STATUS_ACTIVE,
            monthly_lead_quota=plans.BASIC.monthly_lead_quota,
            period_start=now,
            period_end=now + timedelta(days=30),
        )
    )
    with pytest.raises(Exception):
        db_session.commit()
    db_session.rollback()
