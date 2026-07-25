// Search feature API client.
// Client-side helpers that call the Next.js route handlers under /api/projects
// (never the backend directly).
import type { SearchHistoryItem } from "@/lib/types"

interface SearchHistoryResult {
  success: boolean
  searches?: SearchHistoryItem[]
  message?: string
}

export const searchApi = {
  async history(projectId: string): Promise<SearchHistoryResult> {
    const response = await fetch(`/api/projects/${projectId}/searches`)
    return response.json()
  },
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
