// Leads feature API client.
// Client-side helpers that call the Next.js route handlers under /api/projects
// (never the backend directly).
import type { Lead, LeadSaveItem, LeadSaveResult } from "@/lib/types"

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

interface LeadListResult {
  success: boolean
  leads?: Lead[]
  message?: string
}

export type LeadExportFormat = "csv" | "xlsx"

/** Filters shared by the leads list and export. */
export interface LeadListFilters {
  status?: string
  q?: string
}

// Build the query string for the list/export routes from the active filters,
// dropping empty values so they read as "no filter" on the backend.
function buildLeadQuery(filters: LeadListFilters = {}): URLSearchParams {
  const query = new URLSearchParams()
  if (filters.status) query.set("status", filters.status)
  if (filters.q && filters.q.trim()) query.set("q", filters.q.trim())
  return query
}

export const leadsApi = {
  /** List a project's saved leads filtered by status and/or a name search. */
  async list(
    projectId: string,
    filters: LeadListFilters = {},
  ): Promise<LeadListResult> {
    const query = buildLeadQuery(filters)
    const suffix = query.toString() ? `?${query.toString()}` : ""
    const response = await fetch(`/api/projects/${projectId}/leads${suffix}`)
    return response.json()
  },

  /**
   * URL of the export download for the current filters. Rendered as an anchor
   * href (or navigated to) so the browser handles the attachment natively.
   */
  exportUrl(
    projectId: string,
    format: LeadExportFormat,
    filters: LeadListFilters = {},
  ): string {
    const query = buildLeadQuery(filters)
    query.set("format", format)
    return `/api/projects/${projectId}/leads/export?${query.toString()}`
  },

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
