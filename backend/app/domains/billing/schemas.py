from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
