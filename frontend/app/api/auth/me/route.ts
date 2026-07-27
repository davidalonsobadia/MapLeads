import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"

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

    // Call real backend API
    const data = await apiFetch(config.api.endpoints.backend.auth.me, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    return NextResponse.json({
      success: true,
      user: data.user || data,
    })
  } catch (error) {
    console.error("[MapLeads] Get current user error:", error)

    if (error instanceof ApiError) {
      // If unauthorized, clear the cookie
      if (error.status === 401) {
        const cookieStore = await cookies()
        cookieStore.delete("auth-token")
      }

      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to get user" },
      { status: 500 },
    )
  }
}

/**
 * Update the current user's profile (name and/or language).
 * Proxies PATCH /api/v1/auth/me to the backend, forwarding the auth token.
 */
export async function PATCH(request: NextRequest) {
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
    const payload: { name?: string; language?: string } = {}
    if (typeof body.name === "string") payload.name = body.name
    if (typeof body.language === "string") payload.language = body.language

    const data = await apiFetch(config.api.endpoints.backend.auth.me, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    })

    return NextResponse.json({
      success: true,
      user: data.user || data,
    })
  } catch (error) {
    console.error("[MapLeads] Update current user error:", error)

    if (error instanceof ApiError) {
      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Failed to update user" },
      { status: 500 },
    )
  }
}
