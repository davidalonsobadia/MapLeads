"use client"

import Link from "next/link"
import { Archive, ArchiveRestore, MoreVertical, Pencil, Trash2 } from "lucide-react"
import { useTranslations } from "next-intl"
import type { Project } from "@/lib/types"
import { config } from "@/lib/config"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardHeader, CardTitle } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface ProjectItemProps {
  project: Project
  onRename: (project: Project) => void
  onToggleArchive: (project: Project) => void
  onDelete: (project: Project) => void
}

function formatDate(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ""
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
}

export function ProjectItem({ project, onRename, onToggleArchive, onDelete }: ProjectItemProps) {
  const t = useTranslations("projects")
  return (
    <Card className="py-4">
      <CardHeader className="px-4">
        <CardTitle className="flex items-center gap-2 text-base">
          <Link href={config.routes.project(project.id)} className="truncate hover:underline">
            {project.name}
          </Link>
          {project.archived && (
            <Badge variant="secondary" className="shrink-0">
              {t("archivedBadge")}
            </Badge>
          )}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          {t("createdAt", { date: formatDate(project.createdAt) })}
        </p>

        <CardAction>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label={t("actionsFor", { name: project.name })}>
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onRename(project)}>
                <Pencil className="mr-2 h-4 w-4" />
                {t("rename")}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onToggleArchive(project)}>
                {project.archived ? (
                  <>
                    <ArchiveRestore className="mr-2 h-4 w-4" />
                    {t("unarchive")}
                  </>
                ) : (
                  <>
                    <Archive className="mr-2 h-4 w-4" />
                    {t("archive")}
                  </>
                )}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive" onClick={() => onDelete(project)}>
                <Trash2 className="mr-2 h-4 w-4" />
                {t("delete")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardAction>
      </CardHeader>
    </Card>
  )
}
