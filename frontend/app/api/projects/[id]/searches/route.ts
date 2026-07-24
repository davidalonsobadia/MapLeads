import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"
import {
  transformSearchHistoryItemResponse,
  type SearchHistoryItemResponse,
} from "@/lib/types"

type RouteContext = { params: Promise<{ id: string }> }

async function getToken() {
  const cookieStore = await cookies()
  return cookieStore.get("auth-token")?.value
}

/**
 * List a project's search history, newest first.
 * Proxies GET /api/v1/projects/{id}/searches to the backend.
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

    const { id } = await params
    const data = await apiFetch<SearchHistoryItemResponse[]>(
      config.api.endpoints.backend.searches.byProject(id),
      {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      },
    )

    return NextResponse.json({
      success: true,
      searches: data.map(transformSearchHistoryItemResponse),
    })
  } catch (error) {
    console.error("[MapLeads] List searches error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to list searches" },
      { status: 500 },
    )
  }
}
