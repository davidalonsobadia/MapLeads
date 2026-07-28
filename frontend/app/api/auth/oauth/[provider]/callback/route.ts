import { type NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { apiFetch, ApiError } from "@/lib/api-client"
import { config } from "@/lib/config"

type RouteContext = { params: Promise<{ provider: string }> }

const ALLOWED_PROVIDERS = ["google", "github"]

/**
 * Complete the OAuth flow for a provider.
 *
 * Verifies the `state` echoed by the provider against the `oauth_state` cookie
 * (CSRF guard), exchanges the `code` for our session token via the backend,
 * sets the `auth-token` cookie (same options as password login) and redirects
 * to the dashboard.
 */
export async function GET(request: NextRequest, { params }: RouteContext) {
  const { provider } = await params

  if (!ALLOWED_PROVIDERS.includes(provider)) {
    return NextResponse.redirect(new URL("/login?error=oauth", request.url))
  }

  const cookieStore = await cookies()

  const code = request.nextUrl.searchParams.get("code")
  const state = request.nextUrl.searchParams.get("state")
  const storedState = cookieStore.get("oauth_state")?.value

  // CSRF guard: the state from the provider must match the one we issued.
  if (!code || !state || !storedState || state !== storedState) {
    cookieStore.delete("oauth_state")
    return NextResponse.redirect(
      new URL("/login?error=oauth_state", request.url),
    )
  }

  try {
    const data = await apiFetch<{ access_token: string; token_type: string }>(
      config.api.endpoints.backend.auth.oauthCallback(provider),
      {
        method: "POST",
        body: JSON.stringify({ code, state }),
      },
    )

    cookieStore.set("auth-token", data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 7, // 7 days
    })
    cookieStore.delete("oauth_state")

    return NextResponse.redirect(new URL("/dashboard", request.url))
  } catch (error) {
    console.error("[MapLeads] OAuth callback error:", error)
    cookieStore.delete("oauth_state")

    if (error instanceof ApiError) {
      // Do not leak backend error details to the URL.
      return NextResponse.redirect(new URL("/login?error=oauth", request.url))
    }

    return NextResponse.redirect(new URL("/login?error=oauth", request.url))
  }
}
