import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"
import { transformProjectResponse, type ProjectResponse } from "@/lib/types"

type RouteContext = { params: Promise<{ id: string }> }

async function getToken() {
  const cookieStore = await cookies()
  return cookieStore.get("auth-token")?.value
}

/**
 * Get a single project by id.
 * Proxies GET /api/v1/projects/{id} to the backend.
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
    const data = await apiFetch<ProjectResponse>(config.api.endpoints.backend.projects.byId(id), {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    })

    return NextResponse.json({ success: true, project: transformProjectResponse(data) })
  } catch (error) {
    console.error("[MapLeads] Get project error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to get project" },
      { status: 500 },
    )
  }
}

/**
 * Rename and/or archive a project (partial update).
 * Proxies PATCH /api/v1/projects/{id} to the backend.
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

    const { id } = await params
    const body = await request.json()

    const payload: { name?: string; archived?: boolean } = {}
    if (typeof body.name === "string") payload.name = body.name
    if (typeof body.archived === "boolean") payload.archived = body.archived

    const data = await apiFetch<ProjectResponse>(config.api.endpoints.backend.projects.byId(id), {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload),
    })

    return NextResponse.json({ success: true, project: transformProjectResponse(data) })
  } catch (error) {
    console.error("[MapLeads] Update project error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to update project" },
      { status: 500 },
    )
  }
}

/**
 * Delete a project.
 * Proxies DELETE /api/v1/projects/{id} to the backend.
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

    const { id } = await params
    await apiFetch(config.api.endpoints.backend.projects.byId(id), {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error("[MapLeads] Delete project error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to delete project" },
      { status: 500 },
    )
  }
}
