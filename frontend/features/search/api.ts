// Search feature API client.
// Client-side helpers that call the Next.js route handlers under /api/projects
// (never the backend directly).
import { config } from "@/lib/config"
import type { SearchHistoryItem } from "@/lib/types"

interface SearchHistoryResult {
  success: boolean
  searches?: SearchHistoryItem[]
  message?: string
}

export const searchApi = {
  /** Fetch a project's search history, newest first. */
  async history(projectId: string): Promise<SearchHistoryResult> {
    const response = await fetch(config.api.endpoints.searches.byProject(projectId))
    return response.json()
  },
}
