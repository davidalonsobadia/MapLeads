// Leads feature API client.
// Client-side helpers that call the Next.js route handlers under /api/projects
// (never the backend directly).
import type { LeadSaveItem, LeadSaveResult } from "@/lib/types"

interface LeadSaveApiResult {
  success: boolean
  result?: LeadSaveResult
  message?: string
  /**
   * HTTP status of the route-handler response. Callers use it to tell a
   * read-only / quota-exhausted rejection (403) apart from other failures.
   */
  status: number
}

export const leadsApi = {
  /**
   * Save the given search results as leads under a project. The backend
   * deduplicates by place_id and enforces the billing quota; a read-only
   * account is rejected with HTTP 403.
   */
  async save(
    projectId: string,
    items: LeadSaveItem[],
  ): Promise<LeadSaveApiResult> {
    const response = await fetch(`/api/projects/${projectId}/leads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items }),
    })
    const data = (await response.json().catch(() => ({}))) as Omit<
      LeadSaveApiResult,
      "status"
    >
    return { ...data, status: response.status }
  },
}
