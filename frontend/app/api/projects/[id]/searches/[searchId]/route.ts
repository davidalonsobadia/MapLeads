import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"
import {
  transformSearchRunResponse,
  type SearchRunResponse,
} from "@/lib/types"

type RouteContext = { params: Promise<{ id: string; searchId: string }> }

async function getToken() {
  const cookieStore = await cookies()
  return cookieStore.get("auth-token")?.value
}

/**
 * Get a single search under a project, with its result snapshot.
 * Proxies GET /api/v1/projects/{id}/searches/{searchId} to the backend.
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

    const { id, searchId } = await params
    const data = await apiFetch<SearchRunResponse>(
      config.api.endpoints.backend.projects.searchById(id, searchId),
      {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      },
    )

    return NextResponse.json({
      success: true,
      run: transformSearchRunResponse(data),
    })
  } catch (error) {
    console.error("[MapLeads] Get search error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to get search" },
      { status: 500 },
    )
  }
}

/**
 * Delete a single search under a project.
 * Proxies DELETE /api/v1/projects/{id}/searches/{searchId} to the backend.
 */
export async function DELETE(_request: NextRequest, { params }: RouteContext) {
  try {
    const token = await getToken()
    if (!token) {
      return NextResponse.json(
        { success: false, message: "Not authenticated" },
        { status: 401 },
      )
    }

    const { id, searchId } = await params
    await apiFetch<void>(
      config.api.endpoints.backend.projects.searchById(id, searchId),
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      },
    )

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error("[MapLeads] Delete search error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to delete search" },
      { status: 500 },
    )
  }
}
