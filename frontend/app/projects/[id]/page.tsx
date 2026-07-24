"use client"

import { use, useCallback, useEffect, useState } from "react"
import Link from "next/link"
import {
  Archive,
  ArchiveRestore,
  ArrowLeft,
  Loader2,
  MapPin,
  MoreVertical,
  Pencil,
  Search,
  Table2,
} from "lucide-react"
import { projectsApi } from "@/features/projects/api"
import { ProjectDialog } from "@/features/projects/project-dialog"
import { SearchHistory } from "@/features/search/search-history"
import { config } from "@/lib/config"
import type { Project } from "@/lib/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function ProjectViewPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)

  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [renameOpen, setRenameOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await projectsApi.get(id)
      if (!result.success || !result.project) {
        setError(result.message || "Failed to load the project.")
        return
      }
      setProject(result.project)
    } catch {
      setError("Failed to load the project.")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  const handleRename = async (name: string) => {
    const result = await projectsApi.update(id, { name })
    if (!result.success) {
      throw new Error(result.message || "Failed to rename the project.")
    }
    await load()
  }

  const handleToggleArchive = async () => {
    if (!project) return
    const result = await projectsApi.update(id, { archived: !project.archived })
    if (!result.success) {
      setError(result.message || "Failed to update the project.")
      return
    }
    await load()
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8">
          <Button variant="ghost" size="sm" asChild className="mb-6">
            <Link href={config.routes.dashboard}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to dashboard
            </Link>
          </Button>
          <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error || "Project not found."}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto space-y-6 px-4 py-8">
        <Button variant="ghost" size="sm" asChild className="-ml-2">
          <Link href={config.routes.dashboard}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to dashboard
          </Link>
        </Button>

        <header className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="truncate text-2xl font-semibold">{project.name}</h1>
              {project.archived && (
                <Badge variant="secondary" className="shrink-0">
                  Archived
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              Manage this project&apos;s searches and saved leads.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button asChild>
              <Link href={config.routes.projectSearch(project.id)}>
                <Search className="mr-2 h-4 w-4" />
                New search
              </Link>
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon" aria-label="Project actions">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setRenameOpen(true)}>
                  <Pencil className="mr-2 h-4 w-4" />
                  Rename
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleToggleArchive}>
                  {project.archived ? (
                    <>
                      <ArchiveRestore className="mr-2 h-4 w-4" />
                      Unarchive
                    </>
                  ) : (
                    <>
                      <Archive className="mr-2 h-4 w-4" />
                      Archive
                    </>
                  )}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <Tabs defaultValue="searches">
          <TabsList>
            <TabsTrigger value="searches">
              <Search className="mr-2 h-4 w-4" />
              Searches
            </TabsTrigger>
            <TabsTrigger value="leads">
              <Table2 className="mr-2 h-4 w-4" />
              Saved leads
            </TabsTrigger>
          </TabsList>

          <TabsContent value="searches" className="mt-4">
            <SearchHistory projectId={project.id} />
          </TabsContent>

          <TabsContent value="leads" className="mt-4">
            <div className="rounded-lg border border-dashed py-12 text-center">
              <MapPin className="mx-auto mb-4 h-10 w-10 text-muted-foreground" />
              <h3 className="text-base font-semibold">Saved leads</h3>
              <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
                Leads you save from a search will appear here.
              </p>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      <ProjectDialog
        open={renameOpen}
        onOpenChange={setRenameOpen}
        mode="rename"
        initialName={project.name}
        onSubmit={handleRename}
      />
    </div>
  )
}
