import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { config } from "@/lib/config"

type RouteContext = { params: Promise<{ id: string }> }

const ALLOWED_FORMATS = new Set(["csv", "xlsx"])

/**
 * Export a project's filtered leads as a CSV or XLSX download.
 *
 * Proxies GET /api/v1/projects/{id}/leads/export, honoring the same `status`
 * and `q` filters as the leads list plus a `format` selector. Unlike the JSON
 * routes this streams the raw binary body back unchanged (via a direct fetch
 * rather than `apiFetch`, which would decode the payload as text and corrupt an
 * XLSX file), preserving the backend's `Content-Type` and `Content-Disposition`
 * so the browser saves the file with the right name and type.
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

    const search = request.nextUrl.searchParams
    const format = search.get("format") === "xlsx" ? "xlsx" : "csv"
    const query = new URLSearchParams({ format })
    const statusFilter = search.get("status")
    const q = search.get("q")
    if (statusFilter) query.set("status", statusFilter)
    if (q && q.trim()) query.set("q", q.trim())

    if (!ALLOWED_FORMATS.has(format)) {
      return NextResponse.json(
        { success: false, message: "Unsupported export format" },
        { status: 400 },
      )
    }

    const url = `${config.api.baseUrl}${config.api.endpoints.backend.projects.leadsExport(
      id,
    )}?${query.toString()}`

    const response = await fetch(url, {
      method: "GET",
      headers: {
        "x-api-key": config.api.apiKey,
        Authorization: `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      let message = `Failed to export leads (HTTP ${response.status})`
      try {
        const body = (await response.json()) as {
          message?: string
          detail?: string
        }
        message = body.message || body.detail || message
      } catch {
        // Non-JSON error body; keep the generic message.
      }
      return NextResponse.json(
        { success: false, message },
        { status: response.status },
      )
    }

    const headers = new Headers()
    const contentType = response.headers.get("content-type")
    const contentDisposition = response.headers.get("content-disposition")
    if (contentType) headers.set("Content-Type", contentType)
    headers.set(
      "Content-Disposition",
      contentDisposition ?? `attachment; filename="leads.${format}"`,
    )

    return new NextResponse(response.body, { status: 200, headers })
  } catch (error) {
    console.error("[MapLeads] Export leads error:", error)
    return NextResponse.json(
      { success: false, message: "Failed to export leads" },
      { status: 500 },
    )
  }
}
