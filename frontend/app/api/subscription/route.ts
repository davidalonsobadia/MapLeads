import { NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"
import {
  transformSubscriptionUsageResponse,
  type SubscriptionUsageResponse,
} from "@/lib/types"

/**
 * Return the current user's plan and usage snapshot.
 * Proxies GET /api/v1/subscription to the backend, forwarding the auth token.
 */
export async function GET() {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get("auth-token")?.value

    if (!token) {
      return NextResponse.json(
        { success: false, message: "Not authenticated" },
        { status: 401 },
      )
    }

    const data = await apiFetch<SubscriptionUsageResponse>(
      config.api.endpoints.backend.subscription.root,
      {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      },
    )

    return NextResponse.json({
      success: true,
      subscription: transformSubscriptionUsageResponse(data),
    })
  } catch (error) {
    console.error("[MapLeads] Get subscription error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to load subscription" },
      { status: 500 },
    )
  }
}
