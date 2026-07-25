import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"
import {
  transformLeadNoteResponse,
  type LeadNoteCreate,
  type LeadNoteResponse,
} from "@/lib/types"

type RouteContext = { params: Promise<{ leadId: string }> }

async function getToken() {
  const cookieStore = await cookies()
  return cookieStore.get("auth-token")?.value
}

/**
 * List a lead's notes and reminders, newest first.
 * Proxies GET /api/v1/leads/{id}/notes to the backend.
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
    const data = await apiFetch<LeadNoteResponse[]>(
      config.api.endpoints.backend.leads.notes(leadId),
      {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      },
    )

    return NextResponse.json({
      success: true,
      notes: data.map(transformLeadNoteResponse),
    })
  } catch (error) {
    console.error("[MapLeads] List lead notes error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to list notes" },
      { status: 500 },
    )
  }
}

/**
 * Add a note or reminder to a lead.
 * Proxies POST /api/v1/leads/{id}/notes to the backend. A reminder without a
 * date is rejected by the backend with 422, which is passed through unchanged.
 */
export async function POST(request: NextRequest, { params }: RouteContext) {
  try {
    const token = await getToken()
    if (!token) {
      return NextResponse.json(
        { success: false, message: "Not authenticated" },
        { status: 401 },
      )
    }

    const { leadId } = await params
    const body = (await request.json().catch(() => null)) as LeadNoteCreate | null

    if (!body || (body.type !== "note" && body.type !== "reminder")) {
      return NextResponse.json(
        { success: false, message: "Invalid request body" },
        { status: 400 },
      )
    }

    const content = typeof body.content === "string" ? body.content.trim() : ""
    if (!content) {
      return NextResponse.json(
        { success: false, message: "Note content is required" },
        { status: 400 },
      )
    }

    const payload: LeadNoteCreate = { type: body.type, content }
    if (body.type === "reminder") {
      if (!body.reminder_date) {
        return NextResponse.json(
          { success: false, message: "A reminder date is required" },
          { status: 400 },
        )
      }
      payload.reminder_date = body.reminder_date
    }

    const data = await apiFetch<LeadNoteResponse>(
      config.api.endpoints.backend.leads.notes(leadId),
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      },
    )

    return NextResponse.json(
      { success: true, note: transformLeadNoteResponse(data) },
      { status: 201 },
    )
  } catch (error) {
    console.error("[MapLeads] Add lead note error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to add note" },
      { status: 500 },
    )
  }
}
