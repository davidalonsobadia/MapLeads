import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"
import { transformProjectResponse, type ProjectResponse } from "@/lib/types"

/**
 * List the current user's projects.
 * Proxies GET /api/v1/projects to the backend, forwarding the auth token.
 */
export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get("auth-token")?.value

    if (!token) {
      return NextResponse.json(
        { success: false, message: "Not authenticated" },
        { status: 401 },
      )
    }

    const includeArchived = request.nextUrl.searchParams.get("include_archived") === "true"
    const endpoint = `${config.api.endpoints.backend.projects.root}?include_archived=${includeArchived}`

    const data = await apiFetch<ProjectResponse[]>(endpoint, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    })

    return NextResponse.json({
      success: true,
      projects: data.map(transformProjectResponse),
    })
  } catch (error) {
    console.error("[MapLeads] List projects error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to list projects" },
      { status: 500 },
    )
  }
}

/**
 * Create a new project.
 * Proxies POST /api/v1/projects to the backend, forwarding the auth token.
 */
export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies()
    const token = cookieStore.get("auth-token")?.value

    if (!token) {
      return NextResponse.json(
        { success: false, message: "Not authenticated" },
        { status: 401 },
      )
    }

    const body = await request.json()

    const data = await apiFetch<ProjectResponse>(config.api.endpoints.backend.projects.root, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name: body.name }),
    })

    return NextResponse.json(
      { success: true, project: transformProjectResponse(data) },
      { status: 201 },
    )
  } catch (error) {
    console.error("[MapLeads] Create project error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to create project" },
      { status: 500 },
    )
  }
}
