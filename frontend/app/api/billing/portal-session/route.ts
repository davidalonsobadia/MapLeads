import { NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"
import type { BillingSessionResponse } from "@/lib/types"

/**
 * Create a Stripe Billing Portal session.
 * Proxies POST /api/v1/billing/portal-session to the backend, forwarding the
 * auth token, and returns the hosted Portal URL where the user can change or
 * cancel their subscription.
 */
export async function POST() {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get("auth-token")?.value

    if (!token) {
      return NextResponse.json(
        { success: false, message: "Not authenticated" },
        { status: 401 },
      )
    }

    const data = await apiFetch<BillingSessionResponse>(
      config.api.endpoints.backend.billing.portalSession,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      },
    )

    return NextResponse.json({ success: true, url: data.url })
  } catch (error) {
    console.error("[MapLeads] Create portal session error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to open the billing portal" },
      { status: 500 },
    )
  }
}
