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
export interface SearchHistoryItemResponse {
  id: number
  project_id: number
  user_id: number
  keyword: string
  location_type: string
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
  locationType: string
  params: Record<string, unknown>
  resultCount: number
  createdAt: string
}

export function transformSearchHistoryItemResponse(
  backend: SearchHistoryItemResponse,
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

/** Human-readable location label for a search history entry. */
export function formatSearchLocation(item: SearchHistoryItem): string {
  const params = item.params ?? {}
  if (item.locationType === "text") {
    const text = params.location_text
    return typeof text === "string" && text.trim() ? text : "Text search"
  }
  // point search: lat/lng + radius_km
  const lat = params.lat
  const lng = params.lng
  const radius = params.radius_km
  if (typeof lat === "number" && typeof lng === "number") {
    const coords = `${lat.toFixed(4)}, ${lng.toFixed(4)}`
    return typeof radius === "number" ? `${coords} · ${radius} km` : coords
  }
  return "Point search"
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
