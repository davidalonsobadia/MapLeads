// Leads feature API client.
// Client-side helpers that call the Next.js route handlers under /api/projects
// (never the backend directly).
import { config } from "@/lib/config"
import type {
  Lead,
  LeadNote,
  LeadNoteType,
  LeadSaveItem,
  LeadSaveResult,
} from "@/lib/types"

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

interface LeadResult {
  success: boolean
  lead?: Lead
  message?: string
}

interface LeadNotesResult {
  success: boolean
  notes?: LeadNote[]
  message?: string
}

interface LeadNoteResult {
  success: boolean
  note?: LeadNote
  message?: string
}

/** Partial lead update: status and/or LinkedIn URL. */
export interface LeadUpdateInput {
  status?: string
  linkedinUrl?: string | null
}

/** New note/reminder payload; `reminderDate` (ISO) is required for reminders. */
export interface LeadNoteInput {
  type: LeadNoteType
  content: string
  reminderDate?: string | null
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

  /** Get one saved lead with its Google data, LinkedIn URL and status. */
  async get(leadId: string): Promise<LeadResult> {
    const response = await fetch(config.api.endpoints.leads.byId(leadId))
    return response.json()
  },

  /** Update a lead's status and/or LinkedIn URL. */
  async update(leadId: string, input: LeadUpdateInput): Promise<LeadResult> {
    const body: { status?: string; linkedin_url?: string | null } = {}
    if (input.status !== undefined) body.status = input.status
    if (input.linkedinUrl !== undefined) body.linkedin_url = input.linkedinUrl
    const response = await fetch(config.api.endpoints.leads.byId(leadId), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    return response.json()
  },

  /** List a lead's notes and reminders, newest first. */
  async listNotes(leadId: string): Promise<LeadNotesResult> {
    const response = await fetch(config.api.endpoints.leads.notes(leadId))
    return response.json()
  },

  /** Add a note or reminder to a lead. */
  async addNote(leadId: string, input: LeadNoteInput): Promise<LeadNoteResult> {
    const response = await fetch(config.api.endpoints.leads.notes(leadId), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        type: input.type,
        content: input.content,
        reminder_date: input.reminderDate ?? null,
      }),
    })
    return response.json()
  },
}
