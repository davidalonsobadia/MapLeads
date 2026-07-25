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
} from "lucide-react"
import type { Project } from "@/lib/types"
import { config } from "@/lib/config"
import { projectsApi } from "@/features/projects/api"
import { ProjectDialog } from "@/features/projects/project-dialog"
import { SearchHistory } from "@/features/search/search-history"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface ProjectViewPageProps {
  params: Promise<{ id: string }>
}

export default function ProjectViewPage({ params }: ProjectViewPageProps) {
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
    if (!result.success || !result.project) {
      throw new Error(result.message || "Failed to rename the project.")
    }
    setProject(result.project)
  }

  const handleToggleArchive = async () => {
    if (!project) return
    const result = await projectsApi.update(id, { archived: !project.archived })
    if (!result.success || !result.project) {
      setError(result.message || "Failed to update the project.")
      return
    }
    setProject(result.project)
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto flex items-center justify-between px-4 py-4">
          <Link href={config.routes.dashboard} className="flex items-center gap-2">
            <MapPin className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">MapLeads</span>
          </Link>
          <Button variant="ghost" size="sm" asChild>
            <Link href={config.routes.dashboard}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to dashboard
            </Link>
          </Button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : error || !project ? (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error || "Project not found."}
          </div>
        ) : (
          <>
            <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-semibold">{project.name}</h1>
                {project.archived && <Badge variant="secondary">Archived</Badge>}
              </div>
              <div className="flex items-center gap-2">
                <Button asChild>
                  <Link href={config.routes.newSearch(id)}>
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
            </div>

            <Tabs defaultValue="searches">
              <TabsList>
                <TabsTrigger value="searches">Searches</TabsTrigger>
                <TabsTrigger value="leads">Saved leads</TabsTrigger>
              </TabsList>
              <TabsContent value="searches" className="mt-6">
                <SearchHistory projectId={id} />
              </TabsContent>
              <TabsContent value="leads" className="mt-6">
                <div className="rounded-lg border border-dashed py-16 text-center">
                  <h3 className="text-lg font-semibold">Saved leads</h3>
                  <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
                    The saved-leads table for this project will appear here.
                  </p>
                </div>
              </TabsContent>
            </Tabs>
          </>
        )}
      </main>

      <ProjectDialog
        open={renameOpen}
        onOpenChange={setRenameOpen}
        mode="rename"
        initialName={project?.name}
        onSubmit={handleRename}
      />
    </div>
  )
}
