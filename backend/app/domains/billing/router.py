from fastapi import APIRouter, Depends, HTTPException, Request, status
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
    body: schemas.CheckoutSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Create a Stripe Checkout session to subscribe the user to ``plan`` and
    return the hosted URL to redirect them to."""
    try:
        plan = body.validate_plan()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    url = StripeBillingService(db).create_checkout_session(current_user, plan)
    return schemas.CheckoutSessionResponse(url=url)


@billing_router.post(
    "/portal-session", response_model=schemas.PortalSessionResponse
)
def create_portal_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Create a Stripe Billing Portal session for the user to manage or cancel
    their subscription and return the hosted URL."""
    url = StripeBillingService(db).create_portal_session(current_user)
    return schemas.PortalSessionResponse(url=url)


@billing_router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive Stripe webhook events and sync the local subscription.

    Authenticated by the Stripe signature header (this path is exempt from the
    API-key middleware), never by ``x-api-key``.
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    return StripeBillingService(db).handle_webhook(payload, signature)
