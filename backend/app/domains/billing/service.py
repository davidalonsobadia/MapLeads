import math
from datetime import datetime, timedelta
from typing import Optional, Tuple

import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import logger
from app.core.config import settings
from app.domains.auth.models import User
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


# Raw Stripe subscription statuses that make the local account read-only. Any
# status not in this set (e.g. "active", "trialing") allows saving leads,
# subject to the quota check applied alongside it.
_STRIPE_READ_ONLY_STATUSES = {
    "past_due",
    "canceled",
    "unpaid",
    "incomplete",
    "incomplete_expired",
    "paused",
}

# Maps a raw Stripe subscription status onto the local status set enforced by
# the ``ck_subscriptions_status`` DB constraint. Unknown statuses fall back to
# "active" so a paid subscription is never left in an invalid state.
_STRIPE_TO_LOCAL_STATUS = {
    "active": plans.STATUS_ACTIVE,
    "trialing": plans.STATUS_TRIALING,
    "past_due": plans.STATUS_PAST_DUE,
    "unpaid": plans.STATUS_PAST_DUE,
    "incomplete": plans.STATUS_PAST_DUE,
    "paused": plans.STATUS_PAST_DUE,
    "canceled": plans.STATUS_CANCELED,
    "incomplete_expired": plans.STATUS_CANCELED,
}


def _local_status_for(stripe_status: str) -> str:
    return _STRIPE_TO_LOCAL_STATUS.get(stripe_status, plans.STATUS_ACTIVE)


def _extract_price_id(stripe_sub: dict) -> Optional[str]:
    """Return the price id of a Stripe subscription's first line item, if any."""
    items = stripe_sub.get("items") or {}
    data = items.get("data") or []
    if not data:
        return None
    price = data[0].get("price") or {}
    return price.get("id")


class StripeBillingService:
    """Bridges MapLeads subscriptions to Stripe Checkout, Billing Portal and webhooks.

    Checkout and Portal endpoints require Stripe to be configured
    (``STRIPE_SECRET_KEY``); the webhook additionally requires
    ``STRIPE_WEBHOOK_SECRET``. When those are absent the corresponding calls
    return 503 rather than failing obscurely, so the app boots without any
    Stripe credentials.

    All Stripe state changes flow through :meth:`handle_webhook`; the checkout
    and portal calls never mutate the local subscription's plan/quota directly
    (Stripe is the source of truth and confirms via the webhook).
    """

    def __init__(self, db: Session):
        self.db = db

    # -- Public API ---------------------------------------------------------

    def create_checkout_session(self, user_id: int, plan: str) -> str:
        """Create a Stripe Checkout subscription session and return its URL."""
        self._require_configured()

        price_id = self._price_id_for_plan(plan)
        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"The '{plan}' plan is not available for checkout yet. "
                    "Its Stripe price is not configured."
                ),
            )

        subscription = SubscriptionService(self.db).get_for_user(user_id)
        customer_id = self._ensure_customer(user_id, subscription)

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            client_reference_id=str(user_id),
            subscription_data={"metadata": {"user_id": str(user_id)}},
            success_url=f"{settings.FRONTEND_URL}/billing?checkout=success",
            cancel_url=f"{settings.FRONTEND_URL}/billing?checkout=cancel",
        )
        return session["url"]

    def create_portal_session(self, user_id: int) -> str:
        """Create a Stripe Billing Portal session and return its URL."""
        self._require_configured()

        subscription = SubscriptionService(self.db).get_for_user(user_id)
        if not subscription.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No billing customer exists for this account yet. Start a "
                    "checkout before opening the billing portal."
                ),
            )

        session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/billing",
        )
        return session["url"]

    def handle_webhook(self, payload: bytes, signature: Optional[str]) -> dict:
        """Verify and dispatch a Stripe webhook, returning the ack payload.

        Raises 503 if the webhook secret is unconfigured and 400 for a missing
        or invalid signature. The API key is set here as well as in
        ``_require_configured`` so ``retrieve`` calls inside the handlers work
        on a fresh worker process that has never served a checkout/portal
        request.
        """
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Billing webhook is not configured.",
            )
        if settings.STRIPE_SECRET_KEY:
            stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Stripe webhook signature.",
            ) from exc

        event_type = event["type"]
        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(event)
        elif event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
        ):
            self._sync_from_stripe_subscription(event["data"]["object"])
        elif event_type == "customer.subscription.deleted":
            self._handle_subscription_deleted(event)
        else:
            logger.info("Ignoring unhandled Stripe event: %s", event_type)

        return {"received": True}

    # -- Internal helpers ---------------------------------------------------

    def _require_configured(self) -> None:
        """Ensure Stripe is configured and set the SDK API key, else raise 503."""
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Billing is not configured.",
            )
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def _ensure_customer(self, user_id: int, subscription: Subscription) -> str:
        """Return the subscription's Stripe customer id, creating one if absent."""
        if subscription.stripe_customer_id:
            return subscription.stripe_customer_id

        user = self.db.query(User).filter(User.id == user_id).first()
        customer = stripe.Customer.create(
            email=user.email if user else None,
            metadata={"user_id": str(user_id)},
        )
        subscription.stripe_customer_id = customer["id"]
        self.db.commit()
        self.db.refresh(subscription)
        return customer["id"]

    def _price_id_for_plan(self, plan: str) -> Optional[str]:
        return {
            plans.PLAN_BASIC: settings.STRIPE_PRICE_BASIC,
            plans.PLAN_PRO: settings.STRIPE_PRICE_PRO,
            plans.PLAN_ENTERPRISE: settings.STRIPE_PRICE_ENTERPRISE,
        }.get(plan) or None

    def _plan_for_price_id(self, price_id: Optional[str]) -> Optional[str]:
        """Reverse-map a Stripe price id to a local plan identifier.

        Guards against an empty-string env var mapping to a plan, which would
        otherwise let a misconfigured deployment silently assign a plan to any
        subscription whose price id is missing.
        """
        if not price_id:
            return None
        mapping = {
            settings.STRIPE_PRICE_BASIC: plans.PLAN_BASIC,
            settings.STRIPE_PRICE_PRO: plans.PLAN_PRO,
            settings.STRIPE_PRICE_ENTERPRISE: plans.PLAN_ENTERPRISE,
        }
        mapping.pop("", None)
        return mapping.get(price_id)

    def _handle_checkout_completed(self, event: dict) -> None:
        session = event["data"]["object"]
        stripe_sub_id = session.get("subscription")
        if not stripe_sub_id:
            logger.warning("checkout.session.completed without a subscription id")
            return
        stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
        self._sync_from_stripe_subscription(
            stripe_sub, customer_id=session.get("customer")
        )

    def _handle_subscription_deleted(self, event: dict) -> None:
        stripe_sub = event["data"]["object"]
        subscription = self._find_subscription(stripe_sub, stripe_sub.get("customer"))
        if subscription is None:
            logger.warning("subscription.deleted for an unknown local subscription")
            return
        subscription.status = plans.STATUS_CANCELED
        subscription.read_only = True
        self.db.commit()

    def _sync_from_stripe_subscription(
        self, stripe_sub: dict, customer_id: Optional[str] = None
    ) -> None:
        """Apply a Stripe subscription object onto the local subscription."""
        customer_id = customer_id or stripe_sub.get("customer")
        subscription = self._find_subscription(stripe_sub, customer_id)
        if subscription is None:
            logger.warning("Stripe subscription event for an unknown local subscription")
            return

        plan_name = self._plan_for_price_id(_extract_price_id(stripe_sub))
        if plan_name is None:
            logger.warning("Stripe subscription with an unrecognized price id; skipping")
            return

        self._apply_paid_plan(
            subscription,
            plan_name=plan_name,
            stripe_status=stripe_sub.get("status", "active"),
            period_start=datetime.utcfromtimestamp(stripe_sub["current_period_start"]),
            period_end=datetime.utcfromtimestamp(stripe_sub["current_period_end"]),
            stripe_customer_id=customer_id,
            stripe_subscription_id=stripe_sub.get("id"),
        )
        self.db.commit()

    def _apply_paid_plan(
        self,
        subscription: Subscription,
        *,
        plan_name: str,
        stripe_status: str,
        period_start: datetime,
        period_end: datetime,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
    ) -> None:
        """Upgrade a local subscription to a paid plan from Stripe state.

        Resets ``leads_used_this_period`` whenever the billing period changes
        (trial-to-paid conversion and every monthly renewal), so a paid period
        always starts with the full quota available and a previously
        quota-locked account is unblocked for the new period. Within the same
        period (e.g. a mid-period payment-method change) usage is preserved.
        """
        plan_obj = plans.PLANS[plan_name]
        period_changed = (
            subscription.period_start != period_start
            or subscription.period_end != period_end
        )

        subscription.plan = plan_name
        subscription.monthly_lead_quota = plan_obj.monthly_lead_quota
        subscription.status = _local_status_for(stripe_status)
        subscription.period_start = period_start
        subscription.period_end = period_end
        subscription.trial_ends_at = None  # a paid plan clears the trial
        if stripe_customer_id:
            subscription.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id:
            subscription.stripe_subscription_id = stripe_subscription_id

        if period_changed:
            subscription.leads_used_this_period = 0

        # Keep the stored flag consistent with the effective state: Stripe
        # reports a non-paying status, or the quota is already exhausted this
        # period. The service layer recomputes read-only from raw fields, but a
        # correct stored value is relied on by any caller reading it directly.
        subscription.read_only = (
            stripe_status in _STRIPE_READ_ONLY_STATUSES
            or subscription.leads_used_this_period >= subscription.monthly_lead_quota
        )

    def _find_subscription(
        self, stripe_sub: dict, customer_id: Optional[str]
    ) -> Optional[Subscription]:
        """Locate the local subscription for a Stripe event.

        Looks up by Stripe customer id first, then falls back to the
        ``user_id`` carried in the subscription metadata (set at checkout).
        A non-integer metadata value is treated as no match rather than raising.
        """
        if customer_id:
            subscription = (
                self.db.query(Subscription)
                .filter(Subscription.stripe_customer_id == customer_id)
                .first()
            )
            if subscription is not None:
                return subscription

        metadata = stripe_sub.get("metadata") or {}
        raw_user_id = metadata.get("user_id")
        if not raw_user_id:
            return None
        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError):
            return None
        return (
            self.db.query(Subscription)
            .filter(Subscription.user_id == user_id)
            .first()
        )
