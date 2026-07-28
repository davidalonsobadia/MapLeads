"use client"

import { useCallback, useEffect, useState } from "react"
import { useTranslations } from "next-intl"
import { Loader2, SearchX } from "lucide-react"
import type { SearchHistoryItem } from "@/lib/types"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { searchApi, formatSearchLocation } from "./api"

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
  const t = useTranslations("search.history")

  const [searches, setSearches] = useState<SearchHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await searchApi.history(projectId)
      if (!result.success) {
        setError(result.message || t("loadFailed"))
        return
      }
      setSearches(result.searches ?? [])
    } catch {
      setError(t("loadFailed"))
    } finally {
      setLoading(false)
    }
  }, [projectId, t])

  useEffect(() => {
    load()
  }, [load])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
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
      <div className="rounded-lg border border-dashed py-16 text-center">
        <SearchX className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
        <h3 className="text-lg font-semibold">{t("empty.title")}</h3>
        <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
          {t("empty.description")}
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("columns.keyword")}</TableHead>
            <TableHead>{t("columns.location")}</TableHead>
            <TableHead>{t("columns.date")}</TableHead>
            <TableHead className="text-right">{t("columns.results")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {searches.map((search) => (
            <TableRow key={search.id}>
              <TableCell className="font-medium">{search.keyword}</TableCell>
              <TableCell className="text-muted-foreground">
                {formatSearchLocation(search)}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatDate(search.createdAt)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {search.resultCount}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
