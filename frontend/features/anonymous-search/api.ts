// Anonymous-search feature API client.
// Client-side helper that calls the Next.js route handler at
// /api/search/anonymous (never the backend directly). The route handler owns
// the httpOnly visitor cookie; this helper only shapes the request/response.
import type { AnonymousSearchResult, SearchRequestPayload } from "@/lib/types"

// Discriminated result so callers can distinguish a successful search, the
// "free search already used" (blocked) case, and a genuine error.
export type AnonymousSearchOutcome =
  | {
      status: "ok"
      results: AnonymousSearchResult[]
      totalAvailable: number
      hiddenCount: number
    }
  | { status: "blocked" }
  | { status: "error"; message: string }

interface AnonymousSearchApiResponse {
  success: boolean
  blocked?: boolean
  message?: string
  results?: AnonymousSearchResult[]
  totalAvailable?: number
  hiddenCount?: number
}

export const anonymousSearchApi = {
  async run(payload: SearchRequestPayload): Promise<AnonymousSearchOutcome> {
    try {
      const response = await fetch("/api/search/anonymous", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      const data = (await response.json()) as AnonymousSearchApiResponse

      if (data.success) {
        return {
          status: "ok",
          results: data.results ?? [],
          totalAvailable: data.totalAvailable ?? 0,
          hiddenCount: data.hiddenCount ?? 0,
        }
      }

      if (data.blocked) {
        return { status: "blocked" }
      }

      return { status: "error", message: data.message ?? "Anonymous search failed" }
    } catch {
      return { status: "error", message: "Network error. Please try again." }
    }
  },
}
