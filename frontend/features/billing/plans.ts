// Purchasable plan catalog for the billing screen.
//
// Mirrors the backend catalog in `backend/app/domains/billing/plans.py`. The
// backend does not expose a plans endpoint, so these figures are duplicated
// here purely to render the "Change plan" options. Prices/quotas are TENTATIVE
// (PRD sec. 6); keep this list in sync with the backend if it changes.
export interface BillingPlan {
  id: string
  name: string
  priceEur: number
  monthlyLeadQuota: number
  description: string
}

export const BILLING_PLANS: BillingPlan[] = [
  {
    id: "basic",
    name: "Basic",
    priceEur: 15,
    monthlyLeadQuota: 200,
    description: "1 active project.",
  },
  {
    id: "pro",
    name: "Pro",
    priceEur: 39,
    monthlyLeadQuota: 800,
    description: "Unlimited active projects.",
  },
  {
    id: "enterprise",
    name: "Enterprise",
    priceEur: 99,
    monthlyLeadQuota: 2500,
    description: "Unlimited active projects.",
  },
]
