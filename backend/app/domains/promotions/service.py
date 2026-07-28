"""Business logic for the promotions domain.

Task 2 (epic #90) adds internal promo-code creation and listing. Customer
redemption and Stripe enforcement land in later tasks.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import PromoCode
from .schemas import PromoCodeCreate


class PromoCodeService:
    """Create and list promo codes for staff/machine callers."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: PromoCodeCreate) -> PromoCode:
        """Persist a new promo code. The code is already normalized (upper-case,
        trimmed) by the schema; a duplicate raises 409."""
        existing = (
            self.db.query(PromoCode).filter(PromoCode.code == data.code).first()
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Promo code '{data.code}' already exists.",
            )
        promo = PromoCode(
            code=data.code,
            discount_type=data.discount_type,
            value=data.value,
            target_plan=data.target_plan,
            max_uses=data.max_uses,
            used_count=0,
        )
        self.db.add(promo)
        self.db.commit()
        self.db.refresh(promo)
        return promo

    def list_codes(self) -> list[PromoCode]:
        """Return every promo code, newest first, for staff visibility."""
        return (
            self.db.query(PromoCode).order_by(PromoCode.id.desc()).all()
        )
