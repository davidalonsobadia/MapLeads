"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { List, Loader2, MapPin, MoreVertical, SearchX, Trash2 } from "lucide-react"
import type { SearchHistoryItem } from "@/lib/types"
import { config } from "@/lib/config"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { LeadsMap, type LeadMarker } from "@/components/map"
import { searchApi, formatSearchLocation, getSearchPoint } from "./api"
import { DeleteSearchDialog } from "./delete-search-dialog"

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
  const tDialog = useTranslations("search.deleteDialog")
  const router = useRouter()

  const [searches, setSearches] = useState<SearchHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<SearchHistoryItem | null>(
    null,
  )
  const [view, setView] = useState<"list" | "map">("list")

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

  const handleConfirmDelete = useCallback(async () => {
    if (!pendingDelete) return
    const searchId = pendingDelete.id
    const result = await searchApi.remove(projectId, searchId)
    if (!result.success) {
      throw new Error(result.message || tDialog("error"))
    }
    // Remove the row locally so the table updates without a full-page reload.
    setSearches((current) => current.filter((search) => search.id !== searchId))
  }, [pendingDelete, projectId, tDialog])

  const openSearch = useCallback(
    (searchId: string) => {
      router.push(config.routes.searchResults(projectId, searchId))
    },
    [router, projectId],
  )

  const markers = useMemo<LeadMarker[]>(
    () =>
      searches.flatMap((search) => {
        const point = getSearchPoint(search)
        return point
          ? [{ id: search.id, lat: point.lat, lng: point.lng, label: search.keyword }]
          : []
      }),
    [searches],
  )

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
    <div className="space-y-3">
      <div className="flex justify-end">
        <ToggleGroup
          type="single"
          variant="outline"
          value={view}
          onValueChange={(value) => {
            if (value === "list" || value === "map") setView(value)
          }}
          aria-label={t("viewToggleAria")}
        >
          <ToggleGroupItem value="list" aria-label={t("listView")}>
            <List className="h-4 w-4" />
          </ToggleGroupItem>
          <ToggleGroupItem value="map" aria-label={t("mapView")}>
            <MapPin className="h-4 w-4" />
          </ToggleGroupItem>
        </ToggleGroup>
      </div>

      {view === "map" ? (
        <div className="space-y-2">
          <div className="h-[480px]">
            <LeadsMap markers={markers} onMarkerClick={openSearch} className="h-full" />
          </div>
          {markers.length < searches.length && (
            <p className="text-xs text-muted-foreground">
              {t("mapTextLocationNote", {
                missing: searches.length - markers.length,
                total: searches.length,
              })}
            </p>
          )}
        </div>
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("columns.keyword")}</TableHead>
                <TableHead>{t("columns.location")}</TableHead>
                <TableHead>{t("columns.date")}</TableHead>
                <TableHead className="text-right">{t("columns.results")}</TableHead>
                <TableHead className="w-12">
                  <span className="sr-only">{t("columns.actions")}</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {searches.map((search) => {
                const open = () => openSearch(search.id)
                return (
                  <TableRow
                    key={search.id}
                    role="button"
                    tabIndex={0}
                    aria-label={t("viewResultsAria", { keyword: search.keyword })}
                    onClick={open}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault()
                        open()
                      }
                    }}
                    className="cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
                  >
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
                    <TableCell className="text-right">
                      {/* Stop propagation so the action never triggers row navigation. */}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={t("rowActionsAria", { keyword: search.keyword })}
                            onClick={(event) => event.stopPropagation()}
                            onKeyDown={(event) => event.stopPropagation()}
                          >
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            variant="destructive"
                            onClick={(event) => {
                              event.stopPropagation()
                              setPendingDelete(search)
                            }}
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            {t("delete")}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <DeleteSearchDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null)
        }}
        keyword={pendingDelete?.keyword ?? ""}
        onConfirm={handleConfirmDelete}
      />
    </div>
  )
}
