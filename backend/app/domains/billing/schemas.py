from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SubscriptionUsage(BaseModel):
    """Plan and usage snapshot returned by ``GET /subscription``.

    ``read_only`` is computed, not merely the stored flag: the account is
    read-only when the monthly quota is exhausted or the trial ended without an
    active paid plan. ``remaining`` never goes below zero and ``trial_days_left``
    is ``None`` for non-trial plans.
    """

    plan: str
    leads_used: int
    monthly_lead_quota: int
    remaining: int
    period_end: datetime
    trial_ends_at: Optional[datetime] = None
    trial_days_left: Optional[int] = None
    read_only: bool
