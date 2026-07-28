"""Tests for the promotions data layer: the ``PromoCode`` and
``PromoCodeRedemption`` models and their database-level constraints.

Tables are created by ``Base.metadata.create_all`` in the ``db_session``
fixture, so no Alembic run is needed here. The check/unique constraints are
enforced by SQLite as part of the table DDL.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.domains.auth.models import User
from app.domains.promotions.models import PromoCode, PromoCodeRedemption


def _make_user(db_session, email="promo@example.com") -> User:
    user = User(
        name="Promo User",
        email=email,
        hashed_password="x",
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_code(db_session, code="SAVE20", **overrides) -> PromoCode:
    defaults = dict(
        code=code,
        discount_type="percentage",
        value=20,
        target_plan="pro",
        max_uses=100,
    )
    defaults.update(overrides)
    promo = PromoCode(**defaults)
    db_session.add(promo)
    db_session.commit()
    db_session.refresh(promo)
    return promo


def test_create_and_read_back_code_and_redemption(db_session):
    user = _make_user(db_session)
    before = datetime.utcnow()
    promo = _make_code(db_session, expires_at=before + timedelta(days=30))

    # Column defaults are applied.
    assert promo.id is not None
    assert promo.used_count == 0
    assert promo.is_active is True

    redemption = PromoCodeRedemption(
        promo_code_id=promo.id,
        user_id=user.id,
        stripe_coupon_id=None,
    )
    db_session.add(redemption)
    db_session.commit()
    db_session.refresh(redemption)

    read = (
        db_session.query(PromoCodeRedemption)
        .filter_by(promo_code_id=promo.id, user_id=user.id)
        .one()
    )
    assert read.id == redemption.id
    assert read.stripe_coupon_id is None
    # redeemed_at defaults to utcnow.
    assert before <= read.redeemed_at <= datetime.utcnow()


def test_duplicate_code_user_redemption_rejected(db_session):
    user = _make_user(db_session)
    promo = _make_code(db_session)

    db_session.add(
        PromoCodeRedemption(promo_code_id=promo.id, user_id=user.id)
    )
    db_session.commit()

    # A second redemption of the same code by the same user violates the
    # unique (promo_code_id, user_id) constraint.
    db_session.add(
        PromoCodeRedemption(promo_code_id=promo.id, user_id=user.id)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_duplicate_code_rejected(db_session):
    _make_code(db_session, code="UNIQUE1")

    db_session.add(
        PromoCode(
            code="UNIQUE1",
            discount_type="fixed_amount",
            value=500,
            max_uses=10,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_invalid_discount_type_rejected(db_session):
    db_session.add(
        PromoCode(
            code="BADTYPE",
            discount_type="bogus",
            value=1,
            max_uses=10,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_invalid_target_plan_rejected(db_session):
    db_session.add(
        PromoCode(
            code="BADPLAN",
            discount_type="percentage",
            value=10,
            target_plan="platinum",
            max_uses=10,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_null_target_plan_allowed(db_session):
    promo = _make_code(db_session, code="ANYPLAN", target_plan=None)
    assert promo.target_plan is None
