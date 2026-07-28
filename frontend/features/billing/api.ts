// Billing feature API client.
// Client-side helpers that call the Next.js route handlers under /api/subscription
// and /api/billing (never the backend directly).
import type { SubscriptionUsage } from "@/lib/types"

interface SubscriptionResult {
  success: boolean
  subscription?: SubscriptionUsage
  message?: string
}

interface BillingSessionResult {
  success: boolean
  url?: string
  message?: string
}

interface RedeemResult {
  success: boolean
  subscription?: SubscriptionUsage
  message?: string
}

export const billingApi = {
  async getSubscription(): Promise<SubscriptionResult> {
    const response = await fetch("/api/subscription")
    return response.json()
  },

  async createCheckoutSession(plan: string): Promise<BillingSessionResult> {
    const response = await fetch("/api/billing/checkout-session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan }),
    })
    return response.json()
  },

  async createPortalSession(): Promise<BillingSessionResult> {
    const response = await fetch("/api/billing/portal-session", {
      method: "POST",
    })
    return response.json()
  },

  async redeemCode(code: string): Promise<RedeemResult> {
    const response = await fetch("/api/promotions/redeem", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    })
    return response.json()
  },
}
