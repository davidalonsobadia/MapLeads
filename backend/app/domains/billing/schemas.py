from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from . import plans


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


class CheckoutSessionRequest(BaseModel):
    """Request body for creating a Stripe Checkout session.

    ``plan`` must be one of the purchasable plans (``trial`` is a provisioning
    state, not a purchasable plan, so it is rejected). The validator raises a
    plain ``ValueError`` so FastAPI turns an unknown plan into a 422 with no
    manual conversion in the router.
    """

    plan: str

    @field_validator("plan")
    @classmethod
    def validate_plan(cls, value: str) -> str:
        if value not in plans.PLANS:
            allowed = ", ".join(sorted(plans.PLANS))
            raise ValueError(f"Unknown plan '{value}'. Choose one of: {allowed}.")
        return value


class CheckoutSessionResponse(BaseModel):
    """The hosted Stripe Checkout URL the client should redirect the user to."""

    url: str


class PortalSessionResponse(BaseModel):
    """The hosted Stripe Billing Portal URL the client should redirect to."""

    url: str


class WebhookResponse(BaseModel):
    """Acknowledgement returned to Stripe after a webhook is processed."""

    received: bool
