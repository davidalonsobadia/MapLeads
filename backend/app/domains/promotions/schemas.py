"""Pydantic request/response models for the promotions domain.

These land with the internal-creation endpoint (Task 2, epic #90). The redeem
schemas arrive in later tasks. Value-range rules that the ``promo_codes`` table
cannot express (e.g. a percentage between 1 and 100) live here as validators so
FastAPI returns 422 on bad input.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

DISCOUNT_TYPES = ("percentage", "fixed_amount", "free_months", "lifetime_free")
TARGET_PLANS = ("basic", "pro", "enterprise")


class PromoCodeCreate(BaseModel):
    """Payload to mint a promo code. Validators raise plain ``ValueError`` so
    FastAPI returns 422 on invalid input.

    ``value`` semantics depend on ``discount_type``:

    * ``percentage`` — a whole percent in 1..100;
    * ``fixed_amount`` — whole euros, >= 1;
    * ``free_months`` — a month count, >= 1;
    * ``lifetime_free`` — no value (must be ``None``).
    """

    code: str
    discount_type: str
    value: int | None = None
    target_plan: str | None = None
    max_uses: int = 1

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, v: str) -> str:
        normalized = v.strip().upper()
        if not normalized:
            raise ValueError("code must not be empty")
        return normalized

    @field_validator("discount_type")
    @classmethod
    def _check_discount_type(cls, v: str) -> str:
        if v not in DISCOUNT_TYPES:
            raise ValueError(f"discount_type must be one of {DISCOUNT_TYPES}")
        return v

    @field_validator("target_plan")
    @classmethod
    def _check_target_plan(cls, v: str | None) -> str | None:
        if v is not None and v not in TARGET_PLANS:
            raise ValueError(f"target_plan must be one of {TARGET_PLANS}")
        return v

    @field_validator("max_uses")
    @classmethod
    def _check_max_uses(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_uses must be >= 1")
        return v

    @model_validator(mode="after")
    def _check_value_for_type(self) -> "PromoCodeCreate":
        if self.discount_type == "lifetime_free":
            if self.value is not None:
                raise ValueError("lifetime_free must not carry a value")
            return self
        if self.value is None:
            raise ValueError(f"{self.discount_type} requires a value")
        if self.discount_type == "percentage":
            if not 1 <= self.value <= 100:
                raise ValueError("percentage value must be in 1..100")
        elif self.value < 1:
            # fixed_amount (whole euros) and free_months (months) share this rule.
            raise ValueError(f"{self.discount_type} value must be >= 1")
        return self


class RedeemRequest(BaseModel):
    """Customer payload to redeem a promo code against their own subscription.

    The code is normalized (trimmed, upper-cased) to match how codes are stored,
    so redemption is case-insensitive. An empty code raises a plain ``ValueError``
    so FastAPI returns 422.
    """

    code: str

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, v: str) -> str:
        normalized = v.strip().upper()
        if not normalized:
            raise ValueError("code must not be empty")
        return normalized


class RedeemResponse(BaseModel):
    """What a successful redemption applied to the user's subscription.

    ``plan`` is the subscription plan after redemption (unchanged for
    money-only discounts). ``comp_until`` / ``comp_lifetime`` reflect any
    locally-granted free access; ``message`` is a human-readable summary.
    """

    discount_type: str
    plan: str
    comp_until: datetime | None = None
    comp_lifetime: bool = False
    message: str


class PromoCodeResponse(BaseModel):
    """Serialized promo code returned to staff callers."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    discount_type: str
    value: int | None
    target_plan: str | None
    max_uses: int
    used_count: int
    expires_at: datetime | None
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None
