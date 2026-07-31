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
import { useTranslations } from "next-intl"
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
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { ScrollArea } from "@/components/ui/scroll-area"
import { LeadsMap, type LeadMarker } from "@/components/map"
import { billingApi } from "@/features/billing/api"
import { leadsApi } from "@/features/leads/api"

import { readSearchRun, searchApi } from "./api"
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
  const t = useTranslations("search.results")

  const [run, setRun] = useState<SearchRun | null>(null)
  const [loading, setLoading] = useState(true)

  const [savedIds, setSavedIds] = useState<Set<string>>(new Set())
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [activeId, setActiveId] = useState<string | null>(null)

  const [subscription, setSubscription] = useState<SubscriptionUsage | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveState, setSaveState] = useState<SaveState>({ type: "idle" })

  const rowRefs = useRef<Record<string, HTMLDivElement | null>>({})

  // Populate the run for this search id. The backend is the source of truth so
  // older / other-device searches work; the sessionStorage stash (from a search
  // just run in this session) is only an optional fast-path to paint instantly.
  const applyRun = useCallback((next: SearchRun) => {
    setRun(next)
    setSavedIds(
      new Set(next.results.filter((r) => r.alreadySaved).map((r) => r.placeId)),
    )
  }, [])

  useEffect(() => {
    let cancelled = false

    const stored = readSearchRun(searchId)
    if (stored) {
      applyRun(stored)
      setLoading(false)
    }

    searchApi
      .get(projectId, searchId)
      .then((result) => {
        if (cancelled) return
        if (result.success && result.run) {
          applyRun(result.run)
        }
      })
      .catch(() => {
        // Non-fatal: fall back to the stashed run (if any) or the unavailable
        // state. Viewing must not error out on a transient fetch failure.
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [projectId, searchId, applyRun])

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
          message: response.message || t("errors.readOnly"),
        })
        // Reflect the read-only state so the button stays disabled, even if the
        // initial subscription fetch never landed (prev is still null).
        setSubscription(
          (prev) =>
            ({ ...(prev ?? {}), readOnly: true }) as SubscriptionUsage,
        )
        return
      }

      if (!response.success || !response.result) {
        setSaveState({
          type: "error",
          message: response.message || t("errors.saveFailed"),
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
            ? t("success.saved", { count: savedCount })
            : t("success.allSaved"),
      })
    } catch {
      setSaveState({ type: "error", message: t("errors.saveFailed") })
    } finally {
      setSaving(false)
    }
  }, [saving, selectedCount, readOnly, results, selectedIds, projectId, t])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2
          className="h-6 w-6 animate-spin text-primary"
          aria-label={t("loading")}
        />
      </div>
    )
  }

  // Legacy row without a stored snapshot (#106): the search recorded results but
  // none can be replayed. Show the "not available" state rather than an error.
  const unavailable = !run || (run.resultCount > 0 && results.length === 0)
  if (unavailable) {
    return (
      <div className="rounded-lg border border-dashed py-16 text-center">
        <SearchX className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
        <h3 className="text-lg font-semibold">{t("unavailable.title")}</h3>
        <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
          {t("unavailable.description")}
        </p>
        <Button asChild className="mt-4">
          <Link href={config.routes.newSearch(projectId)}>
            {t("unavailable.newSearch")}
          </Link>
        </Button>
      </div>
    )
  }

  // A genuinely empty search (0 results) — distinct from the legacy case above.
  if (results.length === 0) {
    return (
      <div className="rounded-lg border border-dashed py-16 text-center">
        <SearchX className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
        <h3 className="text-lg font-semibold">{t("empty.title")}</h3>
        <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
          {t("empty.description")}
        </p>
        <Button asChild className="mt-4">
          <Link href={config.routes.newSearch(projectId)}>
            {t("unavailable.newSearch")}
          </Link>
        </Button>
      </div>
    )
  }

  const savedTotal = results.filter((r) => savedIds.has(r.placeId)).length

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t("title")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("count", { count: results.length })}
            {savedTotal > 0 &&
              ` · ${t("savedSuffix", { count: savedTotal })}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={handleSave}
            disabled={saving || selectedCount === 0 || readOnly}
          >
            {saving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            {t("saveSelected", { count: selectedCount })}
          </Button>
        </div>
      </div>

      {readOnly && (
        <div
          className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/10 px-4 py-3 text-sm"
          role="status"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
          <p>{t("readOnlyBanner")}</p>
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

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[380px_1fr] lg:items-start">
        <div>
          <div className="mb-2 flex items-center gap-2 px-1">
            <Checkbox
              id="select-all-results"
              checked={allSelectableSelected}
              disabled={selectableIds.length === 0}
              onCheckedChange={(value) => toggleSelectAll(value === true)}
              aria-label={t("selectAllAria")}
            />
            <label
              htmlFor="select-all-results"
              className="text-sm text-muted-foreground"
            >
              {t("selectAll", { count: selectableIds.length })}
            </label>
          </div>
          <ScrollArea className="h-[320px] rounded-lg border lg:h-[640px]">
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

        <div className="h-[360px] lg:sticky lg:top-4 lg:h-[640px]">
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
