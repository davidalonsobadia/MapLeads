"""Centralized billing plan configuration.

Plan definitions live here so that quotas, project limits and pricing are
defined in exactly one place and can be imported wherever they are needed
(subscription provisioning, future quota enforcement in #11, Stripe wiring in
#12).

NOTE: The figures below (lead quotas, project limits and prices) are TENTATIVE
(PRD sec. 6). They still need to be confirmed against real Google Places API
pricing before launch. Treat them as placeholders, not final numbers.
"""

from dataclasses import dataclass
from typing import Dict, Optional

# Plan identifiers. `trial` is a provisioning state rather than a purchasable
# plan, so it is intentionally not part of the PLANS catalog below.
PLAN_TRIAL = "trial"
PLAN_BASIC = "basic"
PLAN_PRO = "pro"
PLAN_ENTERPRISE = "enterprise"

# Subscription lifecycle states.
STATUS_TRIALING = "trialing"
STATUS_ACTIVE = "active"
STATUS_PAST_DUE = "past_due"
STATUS_CANCELED = "canceled"


@dataclass(frozen=True)
class Plan:
    """A purchasable plan tier.

    `max_active_projects = None` means the plan allows an unlimited number of
    active projects.
    """

    name: str
    monthly_lead_quota: int
    max_active_projects: Optional[int]  # None == unlimited
    price_eur: int


# Tentative figures (PRD sec. 6) - confirm against Google pricing before launch.
BASIC = Plan(
    name=PLAN_BASIC,
    monthly_lead_quota=200,
    max_active_projects=1,
    price_eur=15,
)
PRO = Plan(
    name=PLAN_PRO,
    monthly_lead_quota=800,
    max_active_projects=None,  # unlimited
    price_eur=39,
)
ENTERPRISE = Plan(
    name=PLAN_ENTERPRISE,
    monthly_lead_quota=2500,
    max_active_projects=None,  # unlimited
    price_eur=99,
)

# Catalog of purchasable plans, keyed by plan identifier.
PLANS: Dict[str, Plan] = {
    BASIC.name: BASIC,
    PRO.name: PRO,
    ENTERPRISE.name: ENTERPRISE,
}

# Trial configuration.
# No credit card required; the trial lasts 15 days from registration.
TRIAL_PERIOD_DAYS = 15
# OPEN DECISION (flag, do not block): the trial monthly lead quota defaults to
# the Basic plan quota (200). Confirm the intended trial quota with product.
TRIAL_LEAD_QUOTA = BASIC.monthly_lead_quota
