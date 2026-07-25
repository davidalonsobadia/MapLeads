import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"
import type { BillingSessionResponse } from "@/lib/types"

/**
 * Create a Stripe Checkout session for the requested plan.
 * Proxies POST /api/v1/billing/checkout-session to the backend, forwarding the
 * auth token, and returns the hosted Checkout URL to redirect the user to.
 */
export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get("auth-token")?.value

    if (!token) {
      return NextResponse.json(
        { success: false, message: "Not authenticated" },
        { status: 401 },
      )
    }

    const body = await request.json()

    const data = await apiFetch<BillingSessionResponse>(
      config.api.endpoints.backend.billing.checkoutSession,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify({ plan: body.plan }),
      },
    )

    return NextResponse.json({ success: true, url: data.url })
  } catch (error) {
    console.error("[MapLeads] Create checkout session error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to start checkout" },
      { status: 500 },
    )
  }
}
