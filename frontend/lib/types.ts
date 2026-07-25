// Domain Types

export interface User {
  id: string
  name: string
  email: string
  password: string
  emailVerified: boolean
  verificationToken?: string
  resetToken?: string
  resetTokenExpiry?: number
  createdAt: string
}

// Backend API response types (snake_case)
export interface ListResponse {
  id: number
  user_id: number
  name: string
  description?: string | null
  color: string
  task_count?: number
  completed_count?: number
  created_at: string
  updated_at: string
}

// Frontend types (camelCase for easier use in components)
export interface List {
  id: string
  userId: string
  title: string
  description?: string
  color: string
  taskCount?: number
  completedCount?: number
  createdAt: string
  updatedAt: string
}

// Backend API response types (snake_case)
export interface TaskResponse {
  id: number
  list_id: number
  title: string
  description?: string | null
  completed: boolean
  priority: "low" | "medium" | "high"
  due_date?: string | null
  created_at: string
  updated_at: string
}

// Frontend types (camelCase for easier use in components)
export interface Task {
  id: string
  listId: string
  title: string
  description?: string
  completed: boolean
  priority: "low" | "medium" | "high"
  dueDate?: string
  createdAt: string
  updatedAt: string
}

// Backend API response types (snake_case)
export interface ProjectResponse {
  id: number
  user_id: number
  name: string
  archived: boolean
  created_at: string
  updated_at?: string | null
}

// Frontend types (camelCase for easier use in components)
export interface Project {
  id: string
  userId: string
  name: string
  archived: boolean
  createdAt: string
  updatedAt?: string
}

export function transformProjectResponse(backendProject: ProjectResponse): Project {
  return {
    id: String(backendProject.id),
    userId: String(backendProject.user_id),
    name: backendProject.name,
    archived: backendProject.archived,
    createdAt: backendProject.created_at,
    updatedAt: backendProject.updated_at || undefined,
  }
}

// Backend API response types (snake_case)
export interface SearchHistoryResponse {
  id: number
  project_id: number
  user_id: number
  keyword: string
  location_type: "text" | "point"
  params: Record<string, unknown>
  result_count: number
  created_at: string
}

// Frontend types (camelCase for easier use in components)
export interface SearchHistoryItem {
  id: string
  projectId: string
  userId: string
  keyword: string
  locationType: "text" | "point"
  params: Record<string, unknown>
  resultCount: number
  createdAt: string
}

export function transformSearchHistoryResponse(
  backend: SearchHistoryResponse,
): SearchHistoryItem {
  return {
    id: String(backend.id),
    projectId: String(backend.project_id),
    userId: String(backend.user_id),
    keyword: backend.keyword,
    locationType: backend.location_type,
    params: backend.params ?? {},
    resultCount: backend.result_count,
    createdAt: backend.created_at,
  }
}

// Request payload for running a search (snake_case, mirrors the backend schema).
export interface SearchRequestPayload {
  keyword: string
  location_type: "text" | "point"
  location_text?: string
  lat?: number
  lng?: number
  radius_km?: number
}

// Backend API response types (snake_case)
export interface SearchResultResponse {
  place_id: string
  name?: string | null
  address?: string | null
  phone?: string | null
  website?: string | null
  category?: string | null
  lat?: number | null
  lng?: number | null
  already_saved: boolean
}

export interface SearchRunResponse {
  search_id: number
  result_count: number
  already_saved_count: number
  results: SearchResultResponse[]
}

// Frontend types (camelCase for easier use in components)
export interface SearchResult {
  placeId: string
  name?: string
  address?: string
  phone?: string
  website?: string
  category?: string
  lat?: number
  lng?: number
  alreadySaved: boolean
}

export interface SearchRun {
  searchId: string
  resultCount: number
  alreadySavedCount: number
  results: SearchResult[]
}

export function transformSearchResult(backend: SearchResultResponse): SearchResult {
  return {
    placeId: backend.place_id,
    name: backend.name || undefined,
    address: backend.address || undefined,
    phone: backend.phone || undefined,
    website: backend.website || undefined,
    category: backend.category || undefined,
    lat: backend.lat ?? undefined,
    lng: backend.lng ?? undefined,
    alreadySaved: backend.already_saved,
  }
}

export function transformSearchRunResponse(backend: SearchRunResponse): SearchRun {
  return {
    searchId: String(backend.search_id),
    resultCount: backend.result_count,
    alreadySavedCount: backend.already_saved_count,
    results: (backend.results ?? []).map(transformSearchResult),
  }
}

// Request payload for saving a search result as a lead (snake_case, mirrors the
// backend LeadSaveItem schema). `name` is required by the backend.
export interface LeadSaveItem {
  place_id: string
  name: string
  address?: string | null
  phone?: string | null
  website?: string | null
  category?: string | null
}

// Backend API response types (snake_case)
export interface LeadResponse {
  id: number
  project_id: number
  user_id: number
  place_id: string
  name: string
  address?: string | null
  phone?: string | null
  website?: string | null
  category?: string | null
  linkedin_url?: string | null
  status: string
  // Optional coordinates. The backend does not populate these yet; they are
  // read when present so the saved-leads map can plot status-colored pins.
  lat?: number | null
  lng?: number | null
  created_at: string
  updated_at?: string | null
}

export interface LeadSaveResultResponse {
  saved: LeadResponse[]
  skipped_place_ids: string[]
}

// Frontend types (camelCase for easier use in components)
export interface Lead {
  id: string
  projectId: string
  userId: string
  placeId: string
  name: string
  address?: string
  phone?: string
  website?: string
  category?: string
  linkedinUrl?: string
  status: string
  lat?: number
  lng?: number
  createdAt: string
  updatedAt?: string
}

export interface LeadSaveResult {
  saved: Lead[]
  skippedPlaceIds: string[]
}

export function transformLeadResponse(backend: LeadResponse): Lead {
  return {
    id: String(backend.id),
    projectId: String(backend.project_id),
    userId: String(backend.user_id),
    placeId: backend.place_id,
    name: backend.name,
    address: backend.address || undefined,
    phone: backend.phone || undefined,
    website: backend.website || undefined,
    category: backend.category || undefined,
    linkedinUrl: backend.linkedin_url || undefined,
    status: backend.status,
    lat: backend.lat ?? undefined,
    lng: backend.lng ?? undefined,
    createdAt: backend.created_at,
    updatedAt: backend.updated_at || undefined,
  }
}

export function transformLeadSaveResultResponse(
  backend: LeadSaveResultResponse,
): LeadSaveResult {
  return {
    saved: (backend.saved ?? []).map(transformLeadResponse),
    skippedPlaceIds: backend.skipped_place_ids ?? [],
  }
}

// A lead timeline entry: a plain note or a follow-up reminder (with a date).
export type LeadNoteType = "note" | "reminder"

// Backend API response types (snake_case)
export interface LeadNoteResponse {
  id: number
  lead_id: number
  type: LeadNoteType
  content: string
  reminder_date?: string | null
  created_at: string
}

// Request payload for adding a note/reminder (snake_case, mirrors the backend
// LeadNoteCreate schema). `reminder_date` is required when type is "reminder".
export interface LeadNoteCreate {
  type: LeadNoteType
  content: string
  reminder_date?: string | null
}

// Frontend types (camelCase for easier use in components)
export interface LeadNote {
  id: string
  leadId: string
  type: LeadNoteType
  content: string
  reminderDate?: string
  createdAt: string
}

export function transformLeadNoteResponse(backend: LeadNoteResponse): LeadNote {
  return {
    id: String(backend.id),
    leadId: String(backend.lead_id),
    type: backend.type,
    content: backend.content,
    reminderDate: backend.reminder_date || undefined,
    createdAt: backend.created_at,
  }
}

// Build a lead-save payload item from a search result. Falls back to the
// place_id when a result has no name, since the backend requires a non-empty one.
export function searchResultToLeadSaveItem(result: SearchResult): LeadSaveItem {
  return {
    place_id: result.placeId,
    name: result.name?.trim() || result.placeId,
    address: result.address ?? null,
    phone: result.phone ?? null,
    website: result.website ?? null,
    category: result.category ?? null,
  }
}

// Backend API response types (snake_case)
export interface SubscriptionUsageResponse {
  plan: string
  status: string
  leads_used: number
  monthly_lead_quota: number
  remaining: number
  period_end: string
  trial_ends_at?: string | null
  trial_days_left: number
  read_only: boolean
}

// Frontend types (camelCase for easier use in components)
export interface SubscriptionUsage {
  plan: string
  status: string
  leadsUsed: number
  monthlyLeadQuota: number
  remaining: number
  periodEnd: string
  trialEndsAt?: string
  trialDaysLeft: number
  readOnly: boolean
}

export function transformSubscriptionUsageResponse(
  backend: SubscriptionUsageResponse,
): SubscriptionUsage {
  return {
    plan: backend.plan,
    status: backend.status,
    leadsUsed: backend.leads_used,
    monthlyLeadQuota: backend.monthly_lead_quota,
    remaining: backend.remaining,
    periodEnd: backend.period_end,
    trialEndsAt: backend.trial_ends_at || undefined,
    trialDaysLeft: backend.trial_days_left,
    readOnly: backend.read_only,
  }
}

export interface AuthResponse {
  success: boolean
  message?: string
  user?: Omit<User, "password">
  token?: string
}

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

// Transformation utilities to convert between backend and frontend types
export function transformListResponse(backendList: ListResponse): List {
  return {
    id: String(backendList.id),
    userId: String(backendList.user_id),
    title: backendList.name,
    description: backendList.description || undefined,
    color: backendList.color,
    taskCount: backendList.task_count,
    completedCount: backendList.completed_count,
    createdAt: backendList.created_at,
    updatedAt: backendList.updated_at,
  }
}

export function transformTaskResponse(backendTask: TaskResponse): Task {
  return {
    id: String(backendTask.id),
    listId: String(backendTask.list_id),
    title: backendTask.title,
    description: backendTask.description || undefined,
    completed: backendTask.completed,
    priority: backendTask.priority,
    dueDate: backendTask.due_date || undefined,
    createdAt: backendTask.created_at,
    updatedAt: backendTask.updated_at,
  }
}
