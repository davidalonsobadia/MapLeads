// Search feature API client.
// Client-side helpers that call the Next.js route handlers under /api/projects
// (never the backend directly).
import type {
  SearchHistoryItem,
  SearchRequestPayload,
  SearchRun,
} from "@/lib/types"

interface SearchHistoryResult {
  success: boolean
  searches?: SearchHistoryItem[]
  message?: string
}

interface SearchRunResult {
  success: boolean
  run?: SearchRun
  message?: string
}

export const searchApi = {
  async history(projectId: string): Promise<SearchHistoryResult> {
    const response = await fetch(`/api/projects/${projectId}/searches`)
    return response.json()
  },

  async run(
    projectId: string,
    payload: SearchRequestPayload,
  ): Promise<SearchRunResult> {
    const response = await fetch(`/api/projects/${projectId}/searches`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    return response.json()
  },
}

// Hand-off between the new-search screen and the results screen (#20).
// The run is stashed in sessionStorage keyed by its search id; the results
// screen reads it back from the `search_id` it receives in the URL. This keeps
// the (potentially large) result set out of the URL and survives a reload.
const RUN_STORAGE_PREFIX = "mapleads:search-run:"

export function stashSearchRun(run: SearchRun): void {
  if (typeof window === "undefined") return
  try {
    window.sessionStorage.setItem(
      `${RUN_STORAGE_PREFIX}${run.searchId}`,
      JSON.stringify(run),
    )
  } catch {
    // Ignore storage failures (quota/private mode); the results screen can
    // still refetch from history if needed.
  }
}

export function readSearchRun(searchId: string): SearchRun | null {
  if (typeof window === "undefined") return null
  try {
    const raw = window.sessionStorage.getItem(`${RUN_STORAGE_PREFIX}${searchId}`)
    return raw ? (JSON.parse(raw) as SearchRun) : null
  } catch {
    return null
  }
}

/**
 * Human-readable location for a recorded search, derived from its params.
 * Text searches store `location_text`; point searches store `lat`/`lng`/`radius_km`.
 */
export function formatSearchLocation(search: SearchHistoryItem): string {
  const params = search.params
  if (search.locationType === "text") {
    const text = params.location_text
    return typeof text === "string" && text.trim() ? text : "—"
  }

  const lat = params.lat
  const lng = params.lng
  const radius = params.radius_km
  if (typeof lat === "number" && typeof lng === "number") {
    const point = `${lat.toFixed(4)}, ${lng.toFixed(4)}`
    return typeof radius === "number" ? `${point} · ${radius} km` : point
  }
  return "—"
}
