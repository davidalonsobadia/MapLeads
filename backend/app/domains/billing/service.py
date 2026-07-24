import math
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domains.projects.models import Project

from . import plans, schemas
from .models import Subscription


class SubscriptionService:
    """Reads and enforces a user's plan, usage quota and project limits.

    The core billing rule lives here: when the monthly lead quota is exhausted
    (or the trial ends without an active paid plan) the account becomes
    read-only. Read-only blocks *saving new leads* only; searches and reads of
    existing data are never affected.

    NOTE: the quota check (``can_save_leads``) and the increment
    (``record_leads_saved``) run in separate transactions, so two concurrent
    saves that each pass the check can together push usage past the quota. For
    the current scale this is an acceptable trade-off; do not "fix" it by
    caching the subscription between the two calls, which would only widen the
    race. A proper fix needs a row lock or an atomic conditional update.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_for_user(self, user_id: int) -> Subscription:
        """Return the user's subscription, creating a trial one if absent.

        Subscriptions are normally provisioned at registration, but callers
        must not depend on that: this lazily creates a trial subscription so
        pre-existing accounts (and tests) always resolve to a valid record.
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
        """Return the plan/usage snapshot for the user."""
        subscription = self.get_for_user(user_id)
        now = datetime.utcnow()
        remaining = max(
            0, subscription.monthly_lead_quota - subscription.leads_used_this_period
        )
        return schemas.SubscriptionUsage(
            plan=subscription.plan,
            status=subscription.status,
            leads_used=subscription.leads_used_this_period,
            monthly_lead_quota=subscription.monthly_lead_quota,
            remaining=remaining,
            period_end=subscription.period_end,
            trial_ends_at=subscription.trial_ends_at,
            trial_days_left=self._trial_days_left(subscription, now),
            read_only=self._is_read_only(subscription, now),
        )

    def can_save_leads(self, user_id: int, count: int) -> Tuple[bool, Optional[str]]:
        """Whether ``count`` new leads may be saved; returns (allowed, reason).

        ``count <= 0`` (all duplicates) is always allowed since it consumes no
        quota — this guard runs first so a legitimate no-op is never blocked,
        even for a read-only account.
        """
        if count <= 0:
            return True, None

        subscription = self.get_for_user(user_id)
        now = datetime.utcnow()

        if self._is_trial_expired(subscription, now):
            return False, (
                "Your free trial has ended. Upgrade to a paid plan to save new "
                "leads. Your account is read-only; searches and existing data "
                "remain available."
            )

        if (
            subscription.leads_used_this_period + count
            > subscription.monthly_lead_quota
        ):
            return False, (
                f"You have reached your monthly limit of "
                f"{subscription.monthly_lead_quota} saved leads. Your account is "
                "read-only until your quota resets; searches and existing data "
                "remain available. Upgrade your plan for a higher limit."
            )

        return True, None

    def record_leads_saved(self, user_id: int, count: int) -> Subscription:
        """Increment usage by ``count`` and flip ``read_only`` when the quota is hit."""
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
        """Raise 403 when creating another project would exceed the plan limit.

        Only *active* (non-archived) projects count toward the limit; a plan
        limit of ``None`` means unlimited.
        """
        subscription = self.get_for_user(user_id)
        limit = plans.project_limit_for_plan(subscription.plan)
        if limit is None:
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
                    f"Your {subscription.plan} plan allows up to {limit} active "
                    f"project(s). Archive a project or upgrade your plan to "
                    "create more."
                ),
            )

    def _trial_days_left(self, subscription: Subscription, now: datetime) -> int:
        """Whole days remaining in the trial (rounded up), 0 if none/expired."""
        if subscription.trial_ends_at is None:
            return 0
        delta = subscription.trial_ends_at - now
        if delta.total_seconds() <= 0:
            return 0
        return math.ceil(delta.total_seconds() / 86400)

    def _is_trial_expired(self, subscription: Subscription, now: datetime) -> bool:
        """True when a trial subscription's window has elapsed without upgrading."""
        return (
            subscription.plan == plans.PLAN_TRIAL
            and subscription.trial_ends_at is not None
            and now > subscription.trial_ends_at
        )

    def _is_read_only(self, subscription: Subscription, now: datetime) -> bool:
        """Effective read-only state: quota exhausted or trial expired."""
        if self._is_trial_expired(subscription, now):
            return True
        return subscription.leads_used_this_period >= subscription.monthly_lead_quota
