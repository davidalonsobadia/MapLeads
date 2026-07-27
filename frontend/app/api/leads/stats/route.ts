import { NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"
import {
  transformLeadStatsResponse,
  type LeadStatsResponse,
} from "@/lib/types"

/**
 * Return the current user's account-wide lead funnel counts.
 * Proxies GET /api/v1/leads/stats to the backend, forwarding the auth token.
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

    const data = await apiFetch<LeadStatsResponse>(
      config.api.endpoints.backend.leads.stats,
      {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      },
    )

    return NextResponse.json({
      success: true,
      stats: transformLeadStatsResponse(data),
    })
  } catch (error) {
    console.error("[MapLeads] Get lead stats error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to load lead stats" },
      { status: 500 },
    )
  }
}
