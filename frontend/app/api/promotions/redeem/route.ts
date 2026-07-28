import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"

interface RedeemResponse {
  discount_type: string
  plan: string
  comp_until: string | null
  comp_lifetime: boolean
  message: string
}

/**
 * Redeem a promo code against the current user's subscription.
 * Proxies POST /api/v1/promotions/redeem to the backend, forwarding the auth
 * token, and returns a human-readable summary of what the code granted. The
 * client refreshes the subscription snapshot separately after a success.
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

    const data = await apiFetch<RedeemResponse>(
      config.api.endpoints.backend.promotions.redeem,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify({ code: body.code }),
      },
    )

    return NextResponse.json({ success: true, message: data.message })
  } catch (error) {
    console.error("[MapLeads] Redeem promo code error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to redeem code" },
      { status: 500 },
    )
  }
}
