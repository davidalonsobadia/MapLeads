"use client"

import { useCallback, useEffect, useState } from "react"
import { FolderPlus, Loader2, Plus } from "lucide-react"
import type { Project } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { projectsApi } from "./api"
import { ProjectDialog } from "./project-dialog"
import { DeleteProjectDialog } from "./delete-project-dialog"
import { ProjectItem } from "./project-item"

interface ProjectsListProps {
  /** Bump this value to force a reload from the parent (e.g. after an
   *  external "New project" action). */
  refreshKey?: number
}

export function ProjectsList({ refreshKey }: ProjectsListProps = {}) {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [includeArchived, setIncludeArchived] = useState(false)

  const [createOpen, setCreateOpen] = useState(false)
  const [renameTarget, setRenameTarget] = useState<Project | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await projectsApi.list(includeArchived)
      if (!result.success) {
        setError(result.message || "Failed to load projects.")
        return
      }
      setProjects(result.projects ?? [])
    } catch {
      setError("Failed to load projects.")
    } finally {
      setLoading(false)
    }
  }, [includeArchived])

  useEffect(() => {
    load()
  }, [load, refreshKey])

  const handleCreate = async (name: string) => {
    const result = await projectsApi.create(name)
    if (!result.success) {
      throw new Error(result.message || "Failed to create the project.")
    }
    await load()
  }

  const handleRename = async (name: string) => {
    if (!renameTarget) return
    const result = await projectsApi.update(renameTarget.id, { name })
    if (!result.success) {
      throw new Error(result.message || "Failed to rename the project.")
    }
    await load()
  }

  const handleToggleArchive = async (project: Project) => {
    const result = await projectsApi.update(project.id, { archived: !project.archived })
    if (!result.success) {
      setError(result.message || "Failed to update the project.")
      return
    }
    await load()
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    const result = await projectsApi.remove(deleteTarget.id)
    if (!result.success) {
      throw new Error(result.message || "Failed to delete the project.")
    }
    await load()
  }

  return (
    <section>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Projects</h1>
          <p className="text-sm text-muted-foreground">
            Group your searches and leads by client.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Switch
              id="show-archived"
              checked={includeArchived}
              onCheckedChange={setIncludeArchived}
            />
            <Label htmlFor="show-archived" className="text-sm text-muted-foreground">
              Show archived
            </Label>
          </div>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New project
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : projects.length === 0 ? (
        <div className="rounded-lg border border-dashed py-16 text-center">
          <FolderPlus className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
          <h2 className="text-lg font-semibold">No projects yet</h2>
          <p className="mx-auto mt-1 mb-6 max-w-sm text-sm text-muted-foreground">
            Create your first project to start organizing lead searches by client.
          </p>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New project
          </Button>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectItem
              key={project.id}
              project={project}
              onRename={setRenameTarget}
              onToggleArchive={handleToggleArchive}
              onDelete={setDeleteTarget}
            />
          ))}
        </div>
      )}

      <ProjectDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        mode="create"
        onSubmit={handleCreate}
      />

      <ProjectDialog
        open={renameTarget !== null}
        onOpenChange={(open) => {
          if (!open) setRenameTarget(null)
        }}
        mode="rename"
        initialName={renameTarget?.name}
        onSubmit={handleRename}
      />

      <DeleteProjectDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
        projectName={deleteTarget?.name ?? ""}
        onConfirm={handleDelete}
      />
    </section>
  )
}
