import math
from datetime import datetime, timedelta
from typing import Any, Optional, Tuple

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


# Stripe subscription statuses that leave the account unable to save new leads.
# Anything else (``active``/``trialing``) is treated as a healthy paid state.
_STRIPE_READ_ONLY_STATUSES = {"past_due", "canceled", "unpaid", "incomplete_expired"}


class StripeBillingService:
    """Bridges Stripe (Checkout, Billing Portal, webhooks) and the local
    :class:`Subscription` record.

    Session-creation endpoints require Stripe to be configured
    (``STRIPE_SECRET_KEY`` and the relevant price ID); when it is not, they raise
    a 503 rather than making a broken call. The webhook is the sole source of
    truth for subscription state changes: it never trusts the client, only the
    signature-verified event payload.

    ``stripe`` is used at module scope so tests can monkeypatch it; the API key is
    set per call so config changes are picked up without reimporting.
    """

    def __init__(self, db: Session):
        self.db = db
        self.subscriptions = SubscriptionService(db)

    # -- Checkout / Portal ---------------------------------------------------

    def create_checkout_session(self, user: User, plan: str) -> str:
        """Create a Stripe Checkout subscription session and return its URL.

        Reuses the user's ``stripe_customer_id`` when present, creating a Stripe
        customer otherwise. The plan is passed through in metadata and
        ``client_reference_id`` so the webhook can resolve it back to this user.
        """
        self._require_configured()
        price_id = self._price_id_for_plan(plan)
        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Billing is not configured for the '{plan}' plan.",
            )

        subscription = self.subscriptions.get_for_user(user.id)
        customer_id = self._ensure_customer(user, subscription)

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            client_reference_id=str(user.id),
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/billing?checkout=success",
            cancel_url=f"{settings.FRONTEND_URL}/billing?checkout=cancel",
            metadata={"user_id": str(user.id), "plan": plan},
            subscription_data={"metadata": {"user_id": str(user.id), "plan": plan}},
        )
        return session["url"]

    def create_portal_session(self, user: User) -> str:
        """Create a Stripe Billing Portal session and return its URL.

        Requires an existing Stripe customer: a user who has never checked out
        has nothing to manage, so this returns 409 rather than silently creating
        an empty customer.
        """
        self._require_configured()
        subscription = self.subscriptions.get_for_user(user.id)
        if not subscription.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No billing account yet. Subscribe to a plan first.",
            )

        session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/billing",
        )
        return session["url"]

    # -- Webhook -------------------------------------------------------------

    def handle_webhook(self, payload: bytes, signature: Optional[str]) -> dict:
        """Verify and process a Stripe webhook event.

        Raises 400 on a missing/invalid signature. Known subscription-lifecycle
        events sync the local record; anything else is acknowledged and ignored
        so Stripe does not keep retrying events we do not care about.
        """
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Billing webhook is not configured.",
            )

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
        obj = event["data"]["object"]

        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(obj)
        elif event_type == "customer.subscription.updated":
            self._sync_from_stripe_subscription(obj)
        elif event_type == "customer.subscription.deleted":
            self._handle_subscription_deleted(obj)
        else:
            logger.info(f"Ignoring unhandled Stripe event: {event_type}")

        return {"received": True}

    # -- Webhook handlers ----------------------------------------------------

    def _handle_checkout_completed(self, session: Any) -> None:
        """Upgrade the local subscription after a completed Checkout session."""
        subscription = self._find_subscription(
            customer_id=session.get("customer"),
            user_id=session.get("client_reference_id"),
        )
        if subscription is None:
            logger.info("checkout.session.completed for unknown user; ignoring")
            return

        stripe_sub_id = session.get("subscription")
        stripe_sub = None
        if stripe_sub_id:
            stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
            subscription.stripe_subscription_id = stripe_sub_id

        customer_id = session.get("customer")
        if customer_id:
            subscription.stripe_customer_id = customer_id

        metadata = session.get("metadata") or {}
        plan = self._resolve_plan(stripe_sub, metadata.get("plan"))
        self._apply_paid_plan(subscription, plan, stripe_sub)

    def _sync_from_stripe_subscription(self, stripe_sub: Any) -> None:
        """Apply a ``customer.subscription.updated`` event to the local record."""
        subscription = self._find_subscription(
            customer_id=stripe_sub.get("customer"),
            user_id=(stripe_sub.get("metadata") or {}).get("user_id"),
        )
        if subscription is None:
            logger.info("subscription.updated for unknown customer; ignoring")
            return

        subscription.stripe_subscription_id = stripe_sub.get("id")
        plan = self._resolve_plan(
            stripe_sub, (stripe_sub.get("metadata") or {}).get("plan")
        )
        self._apply_paid_plan(subscription, plan, stripe_sub)

    def _handle_subscription_deleted(self, stripe_sub: Any) -> None:
        """Mark the local subscription canceled and read-only."""
        subscription = self._find_subscription(
            customer_id=stripe_sub.get("customer"),
            user_id=(stripe_sub.get("metadata") or {}).get("user_id"),
        )
        if subscription is None:
            logger.info("subscription.deleted for unknown customer; ignoring")
            return

        subscription.status = plans.STATUS_CANCELED
        subscription.read_only = True
        self.db.commit()

    # -- Internal helpers ----------------------------------------------------

    def _apply_paid_plan(
        self, subscription: Subscription, plan: Optional[str], stripe_sub: Any
    ) -> None:
        """Write plan/status/quota/period and clear the trial, then commit."""
        if plan and plan in plans.PLANS:
            subscription.plan = plan
            subscription.monthly_lead_quota = plans.PLANS[plan].monthly_lead_quota

        stripe_status = (stripe_sub or {}).get("status", plans.STATUS_ACTIVE)
        subscription.status = self._map_status(stripe_status)
        subscription.read_only = stripe_status in _STRIPE_READ_ONLY_STATUSES

        period_start = (stripe_sub or {}).get("current_period_start")
        period_end = (stripe_sub or {}).get("current_period_end")
        if period_start:
            subscription.period_start = datetime.utcfromtimestamp(period_start)
        if period_end:
            subscription.period_end = datetime.utcfromtimestamp(period_end)

        # A paid subscription ends the trial.
        subscription.trial_ends_at = None
        self.db.commit()

    def _ensure_customer(self, user: User, subscription: Subscription) -> str:
        """Return the user's Stripe customer id, creating the customer if needed."""
        if subscription.stripe_customer_id:
            return subscription.stripe_customer_id

        customer = stripe.Customer.create(
            email=user.email,
            name=user.name,
            metadata={"user_id": str(user.id)},
        )
        subscription.stripe_customer_id = customer["id"]
        self.db.commit()
        return customer["id"]

    def _find_subscription(
        self, customer_id: Optional[str], user_id: Optional[str]
    ) -> Optional[Subscription]:
        """Locate the local subscription by Stripe customer id, then by user id."""
        if customer_id:
            found = (
                self.db.query(Subscription)
                .filter(Subscription.stripe_customer_id == customer_id)
                .first()
            )
            if found is not None:
                return found
        if user_id:
            try:
                uid = int(user_id)
            except (TypeError, ValueError):
                return None
            return (
                self.db.query(Subscription)
                .filter(Subscription.user_id == uid)
                .first()
            )
        return None

    def _resolve_plan(
        self, stripe_sub: Any, metadata_plan: Optional[str]
    ) -> Optional[str]:
        """Derive the plan from the subscription's price id, else the metadata."""
        price_id = None
        if stripe_sub:
            items = (stripe_sub.get("items") or {}).get("data") or []
            if items:
                price_id = (items[0].get("price") or {}).get("id")
        plan = self._plan_for_price_id(price_id) if price_id else None
        return plan or metadata_plan

    @staticmethod
    def _map_status(stripe_status: str) -> str:
        """Map a Stripe subscription status onto our allowed status set."""
        if stripe_status in {
            plans.STATUS_ACTIVE,
            plans.STATUS_TRIALING,
            plans.STATUS_PAST_DUE,
            plans.STATUS_CANCELED,
        }:
            return stripe_status
        if stripe_status in _STRIPE_READ_ONLY_STATUSES:
            return plans.STATUS_CANCELED
        return plans.STATUS_ACTIVE

    @staticmethod
    def _price_id_for_plan(plan: str) -> str:
        """Return the configured Stripe price id for a plan identifier."""
        return {
            plans.PLAN_BASIC: settings.STRIPE_PRICE_BASIC,
            plans.PLAN_PRO: settings.STRIPE_PRICE_PRO,
            plans.PLAN_ENTERPRISE: settings.STRIPE_PRICE_ENTERPRISE,
        }.get(plan, "")

    @staticmethod
    def _plan_for_price_id(price_id: str) -> Optional[str]:
        """Reverse-map a Stripe price id back to a plan identifier."""
        mapping = {
            settings.STRIPE_PRICE_BASIC: plans.PLAN_BASIC,
            settings.STRIPE_PRICE_PRO: plans.PLAN_PRO,
            settings.STRIPE_PRICE_ENTERPRISE: plans.PLAN_ENTERPRISE,
        }
        # Guard against empty config keys mapping an empty price id to a plan.
        if not price_id:
            return None
        return mapping.get(price_id)

    def _require_configured(self) -> None:
        """Ensure Stripe is usable, setting the API key for this call."""
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Billing is not configured.",
            )
        stripe.api_key = settings.STRIPE_SECRET_KEY
