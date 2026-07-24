from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)

from app.db.base import Base


class Subscription(Base):
    """A user's billing subscription.

    Exactly one subscription exists per user (enforced by the unique
    ``user_id``). A subscription is created at registration in the ``trial``
    plan / ``trialing`` status; Stripe wiring (#12) and quota enforcement (#11)
    build on top of this model.

    The ``user_id`` foreign key intentionally omits an ``ondelete`` rule, so it
    defaults to ``RESTRICT``: a user with a subscription cannot be deleted at
    the DB level. User deletion is not implemented yet; the cascade behavior
    should be decided together with that feature.
    """

    __tablename__ = "subscriptions"
    __table_args__ = (
        # Enforce the documented plan and status sets at the database layer,
        # mirroring the leads domain convention.
        CheckConstraint(
            "plan IN ('trial', 'basic', 'pro', 'enterprise')",
            name="ck_subscriptions_plan",
        ),
        CheckConstraint(
            "status IN ('trialing', 'active', 'past_due', 'canceled')",
            name="ck_subscriptions_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    # One subscription per user.
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        index=True,
        nullable=False,
    )
    # Allowed set: trial | basic | pro | enterprise.
    plan = Column(String, nullable=False)
    # Allowed set: trialing | active | past_due | canceled.
    status = Column(String, nullable=False)
    monthly_lead_quota = Column(Integer, nullable=False)
    leads_used_this_period = Column(Integer, default=0, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)  # renewal date
    trial_ends_at = Column(DateTime, nullable=True)
    read_only = Column(Boolean, default=False, nullable=False)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
