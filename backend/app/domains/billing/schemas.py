from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from . import plans


class CheckoutSessionRequest(BaseModel):
    """Body for creating a Stripe Checkout session.

    ``plan`` must be one of the purchasable plan identifiers (the ``trial`` plan
    is a provisioning state, not something a user can buy).
    """

    plan: str

    def validate_plan(self) -> str:
        """Return the plan if purchasable, else raise a ValueError."""
        if self.plan not in plans.PLANS:
            raise ValueError(f"Unknown plan '{self.plan}'")
        return self.plan


class CheckoutSessionResponse(BaseModel):
    """The hosted Stripe Checkout URL to redirect the user to."""

    url: str


class PortalSessionResponse(BaseModel):
    """The hosted Stripe Billing Portal URL to redirect the user to."""

    url: str


class SubscriptionUsage(BaseModel):
    """The current plan and usage snapshot for a user.

    ``remaining`` is the number of new leads that can still be saved this
    period and ``read_only`` is the effective account state (quota exhausted,
    or trial ended without a paid plan) computed at read time, not a stale flag.
    """

    plan: str
    status: str
    leads_used: int
    monthly_lead_quota: int
    remaining: int
    period_end: datetime
    trial_ends_at: Optional[datetime] = None
    trial_days_left: int
    read_only: bool
