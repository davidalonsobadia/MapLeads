// Projects feature API client.
// Client-side helpers that call the Next.js route handlers under /api/projects
// (never the backend directly).
import type { Project } from "@/lib/types"

interface ProjectResult {
  success: boolean
  project?: Project
  message?: string
}

interface ProjectsResult {
  success: boolean
  projects?: Project[]
  message?: string
}

interface MutationResult {
  success: boolean
  message?: string
}

export const projectsApi = {
  async list(includeArchived = false): Promise<ProjectsResult> {
    const response = await fetch(`/api/projects?include_archived=${includeArchived}`)
    return response.json()
  },

  async get(id: string): Promise<ProjectResult> {
    const response = await fetch(`/api/projects/${id}`)
    return response.json()
  },

  async create(name: string): Promise<ProjectResult> {
    const response = await fetch("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    })
    return response.json()
  },

  async update(id: string, data: { name?: string; archived?: boolean }): Promise<ProjectResult> {
    const response = await fetch(`/api/projects/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    })
    return response.json()
  },

  async remove(id: string): Promise<MutationResult> {
    const response = await fetch(`/api/projects/${id}`, {
      method: "DELETE",
    })
    return response.json()
  },
}
