// Billing feature API client.
// Client-side helpers that call the Next.js route handlers under /api/subscription
// (never the backend directly).
import type { SubscriptionUsage } from "@/lib/types"

interface SubscriptionResult {
  success: boolean
  subscription?: SubscriptionUsage
  message?: string
}

export const billingApi = {
  async getSubscription(): Promise<SubscriptionResult> {
    const response = await fetch("/api/subscription")
    return response.json()
  },
}
