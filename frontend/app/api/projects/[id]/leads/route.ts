import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"
import {
  transformLeadSaveResultResponse,
  type LeadSaveItem,
  type LeadSaveResultResponse,
} from "@/lib/types"

type RouteContext = { params: Promise<{ id: string }> }

/**
 * Save selected search results as leads under a project.
 * Proxies POST /api/v1/projects/{id}/leads to the backend, forwarding the auth
 * token. The backend deduplicates by place_id and enforces the billing quota,
 * so a read-only / quota-exhausted account comes back as a 403 that is passed
 * through unchanged for the client to surface.
 */
export async function POST(request: NextRequest, { params }: RouteContext) {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get("auth-token")?.value

    if (!token) {
      return NextResponse.json(
        { success: false, message: "Not authenticated" },
        { status: 401 },
      )
    }

    const { id } = await params
    const body = (await request.json()) as { items?: LeadSaveItem[] }
    const items = Array.isArray(body.items) ? body.items : []

    if (items.length === 0) {
      return NextResponse.json(
        { success: false, message: "No results selected to save" },
        { status: 400 },
      )
    }

    const data = await apiFetch<LeadSaveResultResponse>(
      config.api.endpoints.backend.projects.leads(id),
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify({ items }),
      },
    )

    return NextResponse.json(
      { success: true, result: transformLeadSaveResultResponse(data) },
      { status: 201 },
    )
  } catch (error) {
    console.error("[MapLeads] Save leads error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to save leads" },
      { status: 500 },
    )
  }
}
