"use client"

// Search-results screen (PRD sec. 4.4, issue #20).
//
// The most important screen: a map with a pin per result and a synced list
// beside it. Hovering or focusing a list row highlights its pin and vice-versa.
// Each result can be selected with a checkbox; results already in the project
// are marked "already in your list" and cannot be selected. "Save selected (N)"
// — the only action that consumes quota — POSTs the checked, non-duplicate
// results to the leads endpoint and marks them saved on success.
//
// Read-only handling: when the subscription reports a read-only / quota-
// exhausted state the save button is disabled with an explanation; searching
// and viewing still work. A 403 from the API (e.g. a race) is handled too.

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Save,
  SearchX,
} from "lucide-react"

import {
  searchResultToLeadSaveItem,
  type SearchResult,
  type SearchRun,
  type SubscriptionUsage,
} from "@/lib/types"
import { config } from "@/lib/config"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { ScrollArea } from "@/components/ui/scroll-area"
import { LeadsMap, type LeadMarker } from "@/components/map"
import { billingApi } from "@/features/billing/api"
import { leadsApi } from "@/features/leads/api"

import { readSearchRun } from "./api"
import { SearchResultItem } from "./search-result-item"

interface SearchResultsProps {
  projectId: string
  searchId: string
}

type SaveState =
  | { type: "idle" }
  | { type: "error"; message: string }
  | { type: "success"; message: string }

export function SearchResults({ projectId, searchId }: SearchResultsProps) {
  const [run, setRun] = useState<SearchRun | null>(null)
  const [loaded, setLoaded] = useState(false)

  const [savedIds, setSavedIds] = useState<Set<string>>(new Set())
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [activeId, setActiveId] = useState<string | null>(null)

  const [subscription, setSubscription] = useState<SubscriptionUsage | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveState, setSaveState] = useState<SaveState>({ type: "idle" })

  const rowRefs = useRef<Record<string, HTMLDivElement | null>>({})

  // Load the stashed run for this search id (client-only; survives a reload).
  useEffect(() => {
    const stored = readSearchRun(searchId)
    if (stored) {
      setRun(stored)
      setSavedIds(
        new Set(stored.results.filter((r) => r.alreadySaved).map((r) => r.placeId)),
      )
    }
    setLoaded(true)
  }, [searchId])

  // Load the subscription snapshot to know whether the account is read-only.
  useEffect(() => {
    let cancelled = false
    billingApi
      .getSubscription()
      .then((result) => {
        if (!cancelled && result.success && result.subscription) {
          setSubscription(result.subscription)
        }
      })
      .catch(() => {
        // Non-fatal: viewing still works, we just can't pre-disable the button.
      })
    return () => {
      cancelled = true
    }
  }, [])

  const results = useMemo(() => run?.results ?? [], [run])
  const readOnly = subscription?.readOnly ?? false

  const isSaved = useCallback(
    (result: SearchResult) => savedIds.has(result.placeId),
    [savedIds],
  )

  const selectableIds = useMemo(
    () => results.filter((r) => !savedIds.has(r.placeId)).map((r) => r.placeId),
    [results, savedIds],
  )

  const allSelectableSelected =
    selectableIds.length > 0 &&
    selectableIds.every((id) => selectedIds.has(id))

  const markers = useMemo<LeadMarker[]>(
    () =>
      results
        .filter(
          (r): r is SearchResult & { lat: number; lng: number } =>
            typeof r.lat === "number" && typeof r.lng === "number",
        )
        .map((r) => ({
          id: r.placeId,
          lat: r.lat,
          lng: r.lng,
          label: r.name,
          // Green pins mark results already in the list; blue = still savable.
          status: savedIds.has(r.placeId) ? "interested" : "new",
        })),
    [results, savedIds],
  )

  const toggleSelected = useCallback((placeId: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (checked) next.add(placeId)
      else next.delete(placeId)
      return next
    })
  }, [])

  const toggleSelectAll = useCallback(
    (checked: boolean) => {
      setSelectedIds(checked ? new Set(selectableIds) : new Set())
    },
    [selectableIds],
  )

  const focusResult = useCallback((placeId: string) => {
    setActiveId(placeId)
    rowRefs.current[placeId]?.scrollIntoView({
      block: "nearest",
      behavior: "smooth",
    })
  }, [])

  const selectedCount = selectedIds.size

  const handleSave = useCallback(async () => {
    if (saving || selectedCount === 0 || readOnly) return

    const items = results
      .filter((r) => selectedIds.has(r.placeId))
      .map(searchResultToLeadSaveItem)

    setSaving(true)
    setSaveState({ type: "idle" })
    try {
      const response = await leadsApi.save(projectId, items)

      if (response.status === 403) {
        setSaveState({
          type: "error",
          message:
            response.message ||
            "Your plan is read-only right now, so saving is disabled. " +
              "Upgrade or wait for your quota to reset to keep saving leads.",
        })
        // Reflect the read-only state so the button stays disabled.
        setSubscription((prev) => (prev ? { ...prev, readOnly: true } : prev))
        return
      }

      if (!response.success || !response.result) {
        setSaveState({
          type: "error",
          message: response.message || "Failed to save the selected leads.",
        })
        return
      }

      // Everything we sent is now in the list (whether freshly saved or a
      // duplicate the backend skipped). Mark them saved and clear the selection.
      const sentIds = items.map((item) => item.place_id)
      setSavedIds((prev) => new Set([...prev, ...sentIds]))
      setSelectedIds(new Set())

      const savedCount = response.result.saved.length
      setSaveState({
        type: "success",
        message:
          savedCount > 0
            ? `Saved ${savedCount} ${savedCount === 1 ? "lead" : "leads"} to this project.`
            : "Those results were already in your list.",
      })
    } catch {
      setSaveState({ type: "error", message: "Failed to save the selected leads." })
    } finally {
      setSaving(false)
    }
  }, [saving, selectedCount, readOnly, results, selectedIds, projectId])

  if (!loaded) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    )
  }

  if (!run) {
    return (
      <div className="rounded-lg border border-dashed py-16 text-center">
        <SearchX className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
        <h3 className="text-lg font-semibold">Results are no longer available</h3>
        <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
          Search results are not kept after you leave this screen. Run the search
          again to view and save its results.
        </p>
        <Button asChild className="mt-4">
          <Link href={config.routes.newSearch(projectId)}>New search</Link>
        </Button>
      </div>
    )
  }

  const savedTotal = results.filter((r) => savedIds.has(r.placeId)).length

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Search results</h1>
          <p className="text-sm text-muted-foreground">
            {results.length} {results.length === 1 ? "result" : "results"}
            {savedTotal > 0 && ` · ${savedTotal} already in your list`}
          </p>
        </div>
        <Button
          onClick={handleSave}
          disabled={saving || selectedCount === 0 || readOnly}
        >
          {saving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Save selected ({selectedCount})
        </Button>
      </div>

      {readOnly && (
        <div
          className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/10 px-4 py-3 text-sm"
          role="status"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
          <p>
            Your plan is read-only right now (quota exhausted or trial ended), so
            saving is disabled. You can still search and view results — upgrade or
            wait for your quota to reset to keep saving leads.
          </p>
        </div>
      )}

      {saveState.type === "error" && (
        <div
          className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          role="alert"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{saveState.message}</p>
        </div>
      )}

      {saveState.type === "success" && (
        <div
          className="flex items-start gap-2 rounded-md border border-success/40 bg-success/10 px-4 py-3 text-sm text-success"
          role="status"
        >
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{saveState.message}</p>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="order-2 lg:order-1">
          <div className="mb-2 flex items-center gap-2 px-1">
            <Checkbox
              id="select-all-results"
              checked={allSelectableSelected}
              disabled={selectableIds.length === 0}
              onCheckedChange={(value) => toggleSelectAll(value === true)}
              aria-label="Select all savable results"
            />
            <label
              htmlFor="select-all-results"
              className="text-sm text-muted-foreground"
            >
              Select all ({selectableIds.length})
            </label>
          </div>
          <ScrollArea className="h-[280px] rounded-lg border lg:h-[560px]">
            <div className="space-y-2 p-2">
              {results.map((result) => (
                <div
                  key={result.placeId}
                  ref={(el) => {
                    rowRefs.current[result.placeId] = el
                  }}
                >
                  <SearchResultItem
                    result={result}
                    saved={isSaved(result)}
                    selected={selectedIds.has(result.placeId)}
                    active={activeId === result.placeId}
                    hovered={hoveredId === result.placeId}
                    onSelectedChange={(checked) =>
                      toggleSelected(result.placeId, checked)
                    }
                    onHover={(hovered) =>
                      setHoveredId(hovered ? result.placeId : null)
                    }
                    onActivate={() => setActiveId(result.placeId)}
                  />
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>

        <div
          className={cn(
            "order-1 h-[280px] lg:order-2 lg:sticky lg:top-4 lg:h-[600px]",
          )}
        >
          <LeadsMap
            markers={markers}
            hoveredId={hoveredId}
            selectedId={activeId}
            onMarkerHover={setHoveredId}
            onMarkerClick={focusResult}
            className="h-full"
          />
        </div>
      </div>
    </div>
  )
}
