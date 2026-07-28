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
