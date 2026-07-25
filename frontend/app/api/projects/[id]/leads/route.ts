import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"
import {
  transformLeadResponse,
  transformLeadSaveResultResponse,
  type LeadResponse,
  type LeadSaveItem,
  type LeadSaveResultResponse,
} from "@/lib/types"

type RouteContext = { params: Promise<{ id: string }> }

/**
 * List a project's saved leads, optionally filtered by status and a
 * case-insensitive name search. Proxies GET /api/v1/projects/{id}/leads,
 * forwarding the `status` and `q` query parameters to the backend.
 */
export async function GET(request: NextRequest, { params }: RouteContext) {
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

    // Forward only the supported filters, dropping empty values so the backend
    // treats them as absent.
    const search = request.nextUrl.searchParams
    const query = new URLSearchParams()
    const statusFilter = search.get("status")
    const q = search.get("q")
    if (statusFilter) query.set("status", statusFilter)
    if (q && q.trim()) query.set("q", q.trim())

    const suffix = query.toString() ? `?${query.toString()}` : ""
    const data = await apiFetch<LeadResponse[]>(
      `${config.api.endpoints.backend.projects.leads(id)}${suffix}`,
      {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      },
    )

    return NextResponse.json({
      success: true,
      leads: data.map(transformLeadResponse),
    })
  } catch (error) {
    console.error("[MapLeads] List leads error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to list leads" },
      { status: 500 },
    )
  }
}

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
    const body = (await request.json().catch(() => null)) as {
      items?: LeadSaveItem[]
    } | null

    if (!body) {
      return NextResponse.json(
        { success: false, message: "Invalid request body" },
        { status: 400 },
      )
    }

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
