"use client"

import { useCallback, useEffect, useState } from "react"
import { CalendarDays, Loader2, MapPin, SearchX } from "lucide-react"
import { config } from "@/lib/config"
import { formatSearchLocation, type SearchHistoryItem } from "@/lib/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { searchApi } from "./api"

interface SearchHistoryProps {
  projectId: string
}

function formatDate(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ""
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

export function SearchHistory({ projectId }: SearchHistoryProps) {
  const [searches, setSearches] = useState<SearchHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await searchApi.history(projectId)
      if (!result.success) {
        setError(result.message || "Failed to load search history.")
        return
      }
      setSearches(result.searches ?? [])
    } catch {
      setError("Failed to load search history.")
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    load()
  }, [load])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
        {error}
      </div>
    )
  }

  if (searches.length === 0) {
    return (
      <div className="rounded-lg border border-dashed py-12 text-center">
        <SearchX className="mx-auto mb-4 h-10 w-10 text-muted-foreground" />
        <h3 className="text-base font-semibold">No searches yet</h3>
        <p className="mx-auto mt-1 mb-6 max-w-sm text-sm text-muted-foreground">
          Run your first search to start collecting leads for this project.
        </p>
        <Button asChild>
          <a href={config.routes.projectSearch(projectId)}>New search</a>
        </Button>
      </div>
    )
  }

  return (
    <ul className="flex flex-col gap-3">
      {searches.map((search) => (
        <li key={search.id}>
          <Card className="py-4">
            <CardContent className="flex flex-wrap items-center justify-between gap-4 px-4">
              <div className="min-w-0">
                <p className="truncate font-medium">{search.keyword}</p>
                <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{formatSearchLocation(search)}</span>
                  </span>
                  <span className="flex items-center gap-1">
                    <CalendarDays className="h-3.5 w-3.5 shrink-0" />
                    {formatDate(search.createdAt)}
                  </span>
                </div>
              </div>
              <Badge variant="secondary" className="shrink-0">
                {search.resultCount} {search.resultCount === 1 ? "result" : "results"}
              </Badge>
            </CardContent>
          </Card>
        </li>
      ))}
    </ul>
  )
}
