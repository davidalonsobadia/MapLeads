import math
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domains.projects.models import Project

from . import plans, schemas
from .models import Subscription


class SubscriptionService:
    """Exposes plan/usage and enforces the core billing rules.

    When the monthly quota is exhausted, or the trial ended without an active
    paid plan, the account becomes read-only: searches and reads still work but
    saving new leads is blocked. Project creation is capped by the plan's active
    project limit.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_for_user(self, user_id: int) -> Subscription:
        """Return the user's subscription, provisioning a trial if none exists.

        Registration provisions a subscription up front (see ``AuthService``),
        so this normally just fetches it. The lazy-create keeps the service
        robust for users that predate provisioning or are seeded directly.
        """
        subscription = (
            self.db.query(Subscription)
            .filter(Subscription.user_id == user_id)
            .first()
        )
        if subscription is not None:
            return subscription

        now = datetime.utcnow()
        trial_ends_at = now + timedelta(days=plans.TRIAL_PERIOD_DAYS)
        subscription = Subscription(
            user_id=user_id,
            plan=plans.PLAN_TRIAL,
            status=plans.STATUS_TRIALING,
            monthly_lead_quota=plans.TRIAL_LEAD_QUOTA,
            leads_used_this_period=0,
            period_start=now,
            period_end=trial_ends_at,
            trial_ends_at=trial_ends_at,
            read_only=False,
        )
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def usage(self, user_id: int) -> schemas.SubscriptionUsage:
        """Return the current plan/usage snapshot for the user."""
        subscription = self.get_for_user(user_id)
        now = datetime.utcnow()
        remaining = max(
            0, subscription.monthly_lead_quota - subscription.leads_used_this_period
        )
        return schemas.SubscriptionUsage(
            plan=subscription.plan,
            leads_used=subscription.leads_used_this_period,
            monthly_lead_quota=subscription.monthly_lead_quota,
            remaining=remaining,
            period_end=subscription.period_end,
            trial_ends_at=subscription.trial_ends_at,
            trial_days_left=self._trial_days_left(subscription, now),
            read_only=self._is_read_only(subscription, now),
        )

    def can_save_leads(
        self, user_id: int, count: int
    ) -> Tuple[bool, Optional[str]]:
        """Whether ``count`` new leads may be saved, with a reason when not.

        Blocked when the trial ended without a paid plan, or when saving
        ``count`` more leads would exceed the monthly quota. ``count <= 0``
        (all duplicates) is always allowed since it consumes no quota.
        """
        subscription = self.get_for_user(user_id)
        now = datetime.utcnow()

        if self._is_trial_expired(subscription, now):
            return False, (
                "Your free trial has ended. Upgrade to a paid plan to save new "
                "leads. Your account is read-only; searches and existing data "
                "remain available."
            )

        if count <= 0:
            return True, None

        if subscription.leads_used_this_period + count > subscription.monthly_lead_quota:
            return False, (
                f"Monthly lead quota reached ({subscription.monthly_lead_quota}). "
                "Your account is read-only until the next billing period or a "
                "plan upgrade; searches and existing data remain available."
            )

        return True, None

    def record_leads_saved(self, user_id: int, count: int) -> Subscription:
        """Increment period usage, flipping ``read_only`` on once the quota is hit."""
        subscription = self.get_for_user(user_id)
        if count <= 0:
            return subscription

        subscription.leads_used_this_period += count
        if subscription.leads_used_this_period >= subscription.monthly_lead_quota:
            subscription.read_only = True
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def enforce_project_limit(self, user_id: int) -> None:
        """Raise 403 when creating another project would exceed the plan limit."""
        subscription = self.get_for_user(user_id)
        limit = self._project_limit(subscription)
        if limit is None:  # unlimited
            return

        active_projects = (
            self.db.query(Project)
            .filter(Project.user_id == user_id, Project.archived.is_(False))
            .count()
        )
        if active_projects >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Your {subscription.plan} plan allows at most {limit} active "
                    "project(s). Archive a project or upgrade your plan to add more."
                ),
            )

    # -- internal helpers -------------------------------------------------

    def _project_limit(self, subscription: Subscription) -> Optional[int]:
        """The plan's active-project limit (``None`` means unlimited)."""
        if subscription.plan == plans.PLAN_TRIAL:
            return plans.TRIAL_MAX_ACTIVE_PROJECTS
        plan = plans.PLANS.get(subscription.plan)
        return plan.max_active_projects if plan is not None else None

    def _is_trial_expired(self, subscription: Subscription, now: datetime) -> bool:
        """True when a trial (never upgraded to a paid plan) has lapsed."""
        return (
            subscription.plan == plans.PLAN_TRIAL
            and subscription.trial_ends_at is not None
            and subscription.trial_ends_at < now
        )

    def _is_read_only(self, subscription: Subscription, now: datetime) -> bool:
        quota_exhausted = (
            subscription.leads_used_this_period >= subscription.monthly_lead_quota
        )
        return (
            subscription.read_only
            or quota_exhausted
            or self._is_trial_expired(subscription, now)
        )

    def _trial_days_left(
        self, subscription: Subscription, now: datetime
    ) -> Optional[int]:
        """Whole days remaining in the trial, or ``None`` for non-trial plans."""
        if subscription.plan != plans.PLAN_TRIAL or subscription.trial_ends_at is None:
            return None
        seconds_left = (subscription.trial_ends_at - now).total_seconds()
        if seconds_left <= 0:
            return 0
        return math.ceil(seconds_left / 86400)
