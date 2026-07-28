from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from app.db.base import Base


class PromoCode(Base):
    """A promotional code that grants a discount or comp on a subscription.

    Codes are created internally (Task 2) and redeemed by customers (Task 3);
    this model is the data layer only. ``code`` is stored normalized to
    upper-case by the service layer — the column just guarantees uniqueness.

    The allowed ``discount_type`` and ``target_plan`` sets are enforced at the
    database layer with ``CheckConstraint``s, mirroring the leads/subscriptions
    convention. Value-range validation (e.g. a percentage between 1 and 100)
    is service/schema logic and lives in later tasks, not here.
    """

    __tablename__ = "promo_codes"
    __table_args__ = (
        CheckConstraint(
            "discount_type IN "
            "('percentage', 'fixed_amount', 'free_months', 'lifetime_free')",
            name="ck_promo_codes_discount_type",
        ),
        CheckConstraint(
            "target_plan IS NULL OR "
            "target_plan IN ('basic', 'pro', 'enterprise')",
            name="ck_promo_codes_target_plan",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    # Normalized upper-case code; unique so a code maps to a single promotion.
    code = Column(String, unique=True, index=True, nullable=False)
    # Allowed set: percentage | fixed_amount | free_months | lifetime_free.
    discount_type = Column(String, nullable=False)
    # Meaning depends on discount_type (percent, cents, months); unused for
    # lifetime_free, hence nullable.
    value = Column(Integer, nullable=True)
    # Optional restriction to a single plan; NULL means any plan.
    target_plan = Column(String, nullable=True)
    max_uses = Column(Integer, nullable=False)
    used_count = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PromoCodeRedemption(Base):
    """A single redemption of a :class:`PromoCode` by a user.

    The ``(promo_code_id, user_id)`` pair is unique so a user cannot redeem the
    same code twice. ``stripe_coupon_id`` is populated later (Task 4) when the
    redemption is mirrored into Stripe.
    """

    __tablename__ = "promo_code_redemptions"
    __table_args__ = (
        UniqueConstraint(
            "promo_code_id",
            "user_id",
            name="uq_promo_code_redemptions_code_user",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    promo_code_id = Column(
        Integer,
        ForeignKey("promo_codes.id"),
        index=True,
        nullable=False,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )
    redeemed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # Populated by Task 4 once the redemption is mirrored into Stripe.
    stripe_coupon_id = Column(String, nullable=True)
