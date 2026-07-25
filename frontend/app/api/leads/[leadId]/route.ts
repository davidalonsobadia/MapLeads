import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"
import { transformLeadResponse, type LeadResponse } from "@/lib/types"

type RouteContext = { params: Promise<{ leadId: string }> }

async function getToken() {
  const cookieStore = await cookies()
  return cookieStore.get("auth-token")?.value
}

/**
 * Get a single lead by id.
 * Proxies GET /api/v1/leads/{id} to the backend.
 */
export async function GET(_request: NextRequest, { params }: RouteContext) {
  try {
    const token = await getToken()
    if (!token) {
      return NextResponse.json(
        { success: false, message: "Not authenticated" },
        { status: 401 },
      )
    }

    const { leadId } = await params
    const data = await apiFetch<LeadResponse>(
      config.api.endpoints.backend.leads.byId(leadId),
      {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      },
    )

    return NextResponse.json({ success: true, lead: transformLeadResponse(data) })
  } catch (error) {
    console.error("[MapLeads] Get lead error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to get lead" },
      { status: 500 },
    )
  }
}

/**
 * Update a lead's status and/or LinkedIn URL (partial update).
 * Proxies PATCH /api/v1/leads/{id} to the backend.
 */
export async function PATCH(request: NextRequest, { params }: RouteContext) {
  try {
    const token = await getToken()
    if (!token) {
      return NextResponse.json(
        { success: false, message: "Not authenticated" },
        { status: 401 },
      )
    }

    const { leadId } = await params
    const body = await request.json().catch(() => null)

    if (!body) {
      return NextResponse.json(
        { success: false, message: "Invalid request body" },
        { status: 400 },
      )
    }

    // Forward only the editable fields. `linkedin_url` is passed through even
    // when empty so the user can clear it (sent as null).
    const payload: { status?: string; linkedin_url?: string | null } = {}
    if (typeof body.status === "string") payload.status = body.status
    if ("linkedin_url" in body) {
      const url =
        typeof body.linkedin_url === "string" ? body.linkedin_url.trim() : ""
      payload.linkedin_url = url || null
    }

    const data = await apiFetch<LeadResponse>(
      config.api.endpoints.backend.leads.byId(leadId),
      {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      },
    )

    return NextResponse.json({ success: true, lead: transformLeadResponse(data) })
  } catch (error) {
    console.error("[MapLeads] Update lead error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to update lead" },
      { status: 500 },
    )
  }
}
