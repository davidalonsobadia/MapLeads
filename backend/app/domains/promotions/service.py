"""Business logic for the promotions domain.

Task 2 (epic #90) adds internal promo-code creation and listing. Customer
redemption and Stripe enforcement land in later tasks.
"""

import calendar
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domains.billing import plans
from app.domains.billing.models import Subscription
from app.domains.billing.service import SubscriptionService

from .models import PromoCode, PromoCodeRedemption
from .schemas import PromoCodeCreate, RedeemResponse


def _add_months(dt: datetime, months: int) -> datetime:
    """Return ``dt`` advanced by ``months`` calendar months.

    Clamps the day to the last valid day of the target month (so e.g. Jan 31 +
    1 month is Feb 28/29). Kept dependency-free on purpose — no dateutil.
    """
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


class PromoCodeService:
    """Create and list promo codes for staff/machine callers."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: PromoCodeCreate) -> PromoCode:
        """Persist a new promo code. The code is already normalized (upper-case,
        trimmed) by the schema; a duplicate raises 409."""
        existing = (
            self.db.query(PromoCode).filter(PromoCode.code == data.code).first()
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Promo code '{data.code}' already exists.",
            )
        promo = PromoCode(
            code=data.code,
            discount_type=data.discount_type,
            value=data.value,
            target_plan=data.target_plan,
            max_uses=data.max_uses,
            used_count=0,
        )
        self.db.add(promo)
        self.db.commit()
        self.db.refresh(promo)
        return promo

    def list_codes(self) -> list[PromoCode]:
        """Return every promo code, newest first, for staff visibility."""
        return (
            self.db.query(PromoCode).order_by(PromoCode.id.desc()).all()
        )

    def redeem(self, user_id: int, code: str) -> RedeemResponse:
        """Redeem ``code`` for ``user_id``, applying the local entitlement effects.

        Validation order (see issue #99): unknown code → 404; inactive/expired/
        cap-reached → 400; ``target_plan`` mismatch → 400; a repeat redemption by
        the same user → 409. On success a :class:`PromoCodeRedemption` row is
        created, ``used_count`` is incremented, and the local effects are applied
        per ``discount_type``. No Stripe calls happen here (Task 4).
        """
        normalized = code.strip().upper()
        promo = (
            self.db.query(PromoCode)
            .filter(PromoCode.code == normalized)
            .first()
        )
        if promo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Promo code '{normalized}' not found.",
            )

        now = datetime.utcnow()
        if not promo.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This promo code is no longer active.",
            )
        if promo.expires_at is not None and now > promo.expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This promo code has expired.",
            )
        if promo.used_count >= promo.max_uses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This promo code has reached its redemption limit.",
            )

        subscription = SubscriptionService(self.db).get_for_user(user_id)

        if promo.target_plan is not None and subscription.plan != promo.target_plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This code only applies to the {promo.target_plan} plan.",
            )

        already = (
            self.db.query(PromoCodeRedemption)
            .filter(
                PromoCodeRedemption.promo_code_id == promo.id,
                PromoCodeRedemption.user_id == user_id,
            )
            .first()
        )
        if already is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already redeemed this promo code.",
            )

        self.db.add(
            PromoCodeRedemption(promo_code_id=promo.id, user_id=user_id)
        )
        promo.used_count += 1

        message = self._apply_effects(promo, subscription, now)

        self.db.commit()
        self.db.refresh(subscription)

        return RedeemResponse(
            discount_type=promo.discount_type,
            plan=subscription.plan,
            comp_until=subscription.comp_until,
            comp_lifetime=subscription.comp_lifetime,
            message=message,
        )

    def _resolve_comp_plan(
        self, promo: PromoCode, subscription: Subscription
    ) -> str:
        """Resolve which plan a comp grants: the code's ``target_plan`` if set,
        else the user's current paid plan, else the ``basic`` default (flagged)."""
        if promo.target_plan is not None:
            return promo.target_plan
        if subscription.plan in plans.PLANS:
            return subscription.plan
        # OPEN DECISION (flag, do not block): comp on a non-paid (trial) plan
        # with no target_plan defaults to Basic. Confirm with product (epic #90).
        return plans.PLAN_BASIC

    def _apply_effects(
        self, promo: PromoCode, subscription: Subscription, now: datetime
    ) -> str:
        """Apply the local entitlement effects for ``promo`` and return a message.

        ``percentage`` / ``fixed_amount`` change neither plan nor quota (the money
        effect is Stripe's, Task 4). ``free_months`` grants time-boxed free access
        on the resolved plan; ``lifetime_free`` grants permanent free access.
        """
        if promo.discount_type in ("percentage", "fixed_amount"):
            return (
                "Discount recorded. It will be applied to your next invoice."
            )

        comp_plan = self._resolve_comp_plan(promo, subscription)
        plan_obj = plans.PLANS[comp_plan]
        subscription.plan = comp_plan
        subscription.monthly_lead_quota = plan_obj.monthly_lead_quota
        subscription.status = plans.STATUS_ACTIVE
        subscription.trial_ends_at = None

        if promo.discount_type == "free_months":
            base = max(now, subscription.period_end)
            subscription.comp_until = _add_months(base, promo.value)
            return (
                f"{promo.value} free month(s) on the {comp_plan} plan applied."
            )

        # lifetime_free
        subscription.comp_lifetime = True
        return f"Lifetime free access on the {comp_plan} plan applied."
