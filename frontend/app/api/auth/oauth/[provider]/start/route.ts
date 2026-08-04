import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"

type RouteContext = { params: Promise<{ provider: string }> }

const ALLOWED_PROVIDERS = ["google"]

/**
 * Start the OAuth flow for a provider.
 *
 * Asks the backend for the provider authorization URL and a signed `state`,
 * stashes `state` in a short-lived httpOnly cookie (for the CSRF check on the
 * callback), then 302-redirects the browser to the provider.
 */
export async function GET(_request: NextRequest, { params }: RouteContext) {
  const { provider } = await params

  if (!ALLOWED_PROVIDERS.includes(provider)) {
    return NextResponse.redirect(new URL("/login?error=oauth", config.app.url))
  }

  try {
    const data = await apiFetch<{ authorization_url: string; state: string }>(
      config.api.endpoints.backend.auth.oauthAuthorize(provider),
      { method: "GET" },
    )

    const cookieStore = await cookies()
    cookieStore.set("oauth_state", data.state, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 600, // 10 minutes
    })

    return NextResponse.redirect(data.authorization_url)
  } catch (error) {
    console.error("[MapLeads] OAuth start error:", error)

    if (error instanceof ApiError && error.status === 503) {
      return NextResponse.redirect(
        new URL("/login?error=oauth_unconfigured", config.app.url),
      )
    }

    return NextResponse.redirect(new URL("/login?error=oauth", config.app.url))
  }
}
