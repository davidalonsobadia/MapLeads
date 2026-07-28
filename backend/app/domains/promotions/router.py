"""HTTP routes for the promotions domain.

Task 2 (epic #90) adds internal promo-code creation and listing. Both endpoints
are gated by :func:`require_internal_key` (the ``x-internal-key`` internal
secret), separate from the customer-facing ``x-api-key`` gateway — see
``deps.py`` for why this is an internal secret rather than an ``is_staff`` user
flag. Customer redemption lands in later tasks.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.auth.models import User
from app.domains.auth.utils import get_verified_user

from . import schemas
from .deps import require_internal_key
from .service import PromoCodeService

router = APIRouter(prefix="/promotions", tags=["promotions"])


@router.post(
    "/codes",
    response_model=schemas.PromoCodeResponse,
    dependencies=[Depends(require_internal_key)],
)
def create_promo_code(
    payload: schemas.PromoCodeCreate,
    db: Session = Depends(get_db),
):
    """Create a promo code (internal/staff only). Rejects a duplicate code with
    409; ``used_count`` starts at 0."""
    return PromoCodeService(db).create(payload)


@router.get(
    "/codes",
    response_model=list[schemas.PromoCodeResponse],
    dependencies=[Depends(require_internal_key)],
)
def list_promo_codes(
    db: Session = Depends(get_db),
):
    """List every promo code (internal/staff only) for staff visibility."""
    return PromoCodeService(db).list_codes()


@router.post("/redeem", response_model=schemas.RedeemResponse)
def redeem_promo_code(
    payload: schemas.RedeemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Redeem a promo code against the caller's own subscription.

    Unlike the internal ``/codes`` endpoints, this is a customer action gated by
    the normal verified-user auth. Applies only the local entitlement effects;
    Stripe billing is unaffected until a later task. Returns 404 for an unknown
    code, 400 for an inactive/expired/capped or plan-restricted code, and 409 if
    the caller has already redeemed it."""
    return PromoCodeService(db).redeem(current_user.id, payload.code)
