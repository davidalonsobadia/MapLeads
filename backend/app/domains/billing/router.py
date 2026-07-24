from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.auth.models import User
from app.domains.auth.utils import get_verified_user

from . import schemas
from .service import StripeBillingService, SubscriptionService

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("", response_model=schemas.SubscriptionUsage)
def get_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Return the current user's plan and usage, including quota remaining and
    trial days left."""
    return SubscriptionService(db).usage(current_user.id)


billing_router = APIRouter(prefix="/billing", tags=["billing"])


@billing_router.post(
    "/checkout-session", response_model=schemas.CheckoutSessionResponse
)
def create_checkout_session(
    payload: schemas.CheckoutSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Create a Stripe Checkout subscription session for the target plan and
    return the hosted URL to redirect the user to."""
    url = StripeBillingService(db).create_checkout_session(
        current_user.id, payload.plan
    )
    return schemas.CheckoutSessionResponse(url=url)


@billing_router.post(
    "/portal-session", response_model=schemas.PortalSessionResponse
)
def create_portal_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Create a Stripe Billing Portal session and return the hosted URL where
    the user can change or cancel their subscription."""
    url = StripeBillingService(db).create_portal_session(current_user.id)
    return schemas.PortalSessionResponse(url=url)


@billing_router.post("/webhook", response_model=schemas.WebhookResponse)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive and process Stripe webhooks.

    Authenticated solely by the Stripe signature header (this path is exempt
    from the ``x-api-key`` middleware). Rejects a missing/invalid signature
    with 400 and keeps the local subscription in sync with Stripe.
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    result = StripeBillingService(db).handle_webhook(payload, signature)
    return schemas.WebhookResponse(**result)
