import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"
import {
  transformAnonymousSearchResponse,
  type AnonymousSearchResponse,
  type SearchRequestPayload,
} from "@/lib/types"

// Cookie holding the signed anon-search token. Its lifetime mirrors the backend
// token TTL (ANONYMOUS_SEARCH_TOKEN_TTL_DAYS = 30 days).
const ANON_SEARCH_COOKIE = "anon-search-token"
const ANON_SEARCH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30 // 30 days

/**
 * Run an anonymous "try a search" against the backend.
 * Proxies POST /api/v1/search/anonymous. This flow is unauthenticated: no
 * `auth-token` is read; the visitor's single-search allowance is tracked with
 * the httpOnly `anon-search-token` cookie, replayed as `X-Anonymous-Search-Token`.
 */
export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as SearchRequestPayload

    // Forward only the fields the backend understands.
    const payload: SearchRequestPayload = {
      keyword: body.keyword,
      location_type: body.location_type,
      ...(body.location_text !== undefined && { location_text: body.location_text }),
      ...(body.lat !== undefined && { lat: body.lat }),
      ...(body.lng !== undefined && { lng: body.lng }),
      ...(body.radius_km !== undefined && { radius_km: body.radius_km }),
    }

    const cookieStore = await cookies()
    const visitorToken = cookieStore.get(ANON_SEARCH_COOKIE)?.value

    const data = await apiFetch<AnonymousSearchResponse>(
      config.api.endpoints.backend.search.anonymous,
      {
        method: "POST",
        headers: {
          ...(visitorToken && { "X-Anonymous-Search-Token": visitorToken }),
        },
        body: JSON.stringify(payload),
      },
    )

    const run = transformAnonymousSearchResponse(data)

    // Persist the freshly issued token so the free search reads as spent next time.
    cookieStore.set(ANON_SEARCH_COOKIE, run.visitorToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: ANON_SEARCH_COOKIE_MAX_AGE,
    })

    const hiddenCount = Math.max(0, run.totalAvailable - run.results.length)

    return NextResponse.json({
      success: true,
      results: run.results,
      totalAvailable: run.totalAvailable,
      hiddenCount,
    })
  } catch (error) {
    console.error("[MapLeads] Anonymous search error:", error)

    if (error instanceof ApiError) {
      // A 403 means the single free search is already spent. Surface it as a
      // distinct "blocked" outcome so the UI can prompt sign-up instead of
      // rendering a generic error.
      if (error.status === 403) {
        return NextResponse.json(
          { success: false, blocked: true, message: error.message },
          { status: 403 },
        )
      }

      return NextResponse.json(
        { success: false, message: error.message },
        { status: error.status },
      )
    }

    return NextResponse.json(
      { success: false, message: "Anonymous search failed" },
      { status: 500 },
    )
  }
}
