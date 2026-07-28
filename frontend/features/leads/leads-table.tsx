"use client"

// Saved-leads table for a project (PRD sec. 4.5, issue #21).
//
// Lists a project's saved leads with all their columns and two combinable
// filters — a status dropdown and a case-insensitive name search — both pushed
// to the backend via `GET /projects/{id}/leads?status=&q=`. An "Export" button
// downloads the *currently filtered* set as CSV or XLSX (honoring the same
// filters). A list/map toggle swaps the table for a `<LeadsMap>` (#15) showing
// the same filtered leads as status-colored pins. Clicking a row opens the lead
// detail screen (#22).

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { Download, List, Loader2, MapPin, Users } from "lucide-react"

import type { Lead } from "@/lib/types"
import { config } from "@/lib/config"
import {
  getLeadStatusStyle,
  LEAD_STATUS_STYLES,
  LEAD_STATUSES,
  type LeadStatus,
} from "@/lib/lead-status"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
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
import { leadsApi, type LeadExportFormat } from "./api"

interface LeadsTableProps {
  projectId: string
}

// Sentinel for the status <Select>, since Radix forbids an empty item value.
const ALL_STATUSES = "all"

function formatDate(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ""
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

function StatusBadge({ status }: { status: string }) {
  const t = useTranslations("leads.status")
  const style = getLeadStatusStyle(status)
  return (
    <Badge variant="secondary" className={cn("gap-1.5", style.badgeClass)}>
      <span
        className={cn("h-1.5 w-1.5 rounded-full", style.dotClass)}
        aria-hidden="true"
      />
      {t(status in LEAD_STATUS_STYLES ? status : "new")}
    </Badge>
  )
}

// Only treat http(s) URLs as linkable; anything else (e.g. a `javascript:` URI
// from the external data source) is rendered as plain text.
function safeHref(website?: string) {
  return website && /^https?:\/\//i.test(website) ? website : undefined
}

export function LeadsTable({ projectId }: LeadsTableProps) {
  const router = useRouter()
  const t = useTranslations("leads.table")
  const tStatus = useTranslations("leads.status")

  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [statusFilter, setStatusFilter] = useState<string>(ALL_STATUSES)
  const [searchInput, setSearchInput] = useState("")
  const [query, setQuery] = useState("")
  const [view, setView] = useState<"list" | "map">("list")

  // Debounce the name search so we don't refetch on every keystroke.
  useEffect(() => {
    const handle = setTimeout(() => setQuery(searchInput), 300)
    return () => clearTimeout(handle)
  }, [searchInput])

  const filters = useMemo(
    () => ({
      status: statusFilter === ALL_STATUSES ? undefined : statusFilter,
      q: query.trim() || undefined,
    }),
    [statusFilter, query],
  )

  // Track the latest request so a slow earlier response can't clobber a newer
  // one when filters change quickly.
  const requestId = useRef(0)

  const load = useCallback(async () => {
    const current = ++requestId.current
    setLoading(true)
    setError(null)
    try {
      const result = await leadsApi.list(projectId, filters)
      if (current !== requestId.current) return
      if (!result.success) {
        setError(result.message || t("loadFailed"))
        return
      }
      setLeads(result.leads ?? [])
    } catch {
      if (current !== requestId.current) return
      setError(t("loadFailed"))
    } finally {
      if (current === requestId.current) setLoading(false)
    }
  }, [projectId, filters, t])

  useEffect(() => {
    load()
  }, [load])

  const hasFilters = statusFilter !== ALL_STATUSES || query.trim().length > 0

  const markers = useMemo<LeadMarker[]>(
    () =>
      leads
        .filter(
          (lead): lead is Lead & { lat: number; lng: number } =>
            typeof lead.lat === "number" && typeof lead.lng === "number",
        )
        .map((lead) => ({
          id: lead.id,
          lat: lead.lat,
          lng: lead.lng,
          label: lead.name,
          status: lead.status,
        })),
    [leads],
  )

  const handleExport = useCallback(
    (format: LeadExportFormat) => {
      // Navigate to the export route; its Content-Disposition makes the browser
      // download the file rather than render it.
      const url = leadsApi.exportUrl(projectId, format, filters)
      const anchor = document.createElement("a")
      anchor.href = url
      anchor.rel = "noopener"
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
    },
    [projectId, filters],
  )

  const openLead = useCallback(
    (leadId: string) => {
      router.push(config.routes.lead(projectId, leadId))
    },
    [router, projectId],
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]" aria-label={t("filterByStatus")}>
            <SelectValue placeholder={t("allStatuses")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_STATUSES}>{t("allStatuses")}</SelectItem>
            {LEAD_STATUSES.map((status: LeadStatus) => (
              <SelectItem key={status} value={status}>
                {tStatus(status)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Input
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder={t("searchPlaceholder")}
          className="h-10 max-w-xs flex-1"
          aria-label={t("searchAria")}
        />

        <div className="ml-auto flex items-center gap-2">
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

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" disabled={leads.length === 0}>
                <Download className="mr-2 h-4 w-4" />
                {t("export")}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => handleExport("csv")}>
                {t("exportCsv")}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExport("xlsx")}>
                {t("exportXlsx")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : error ? (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : leads.length === 0 ? (
        <div className="rounded-lg border border-dashed py-16 text-center">
          <Users className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
          <h3 className="text-lg font-semibold">
            {hasFilters ? t("emptyFilteredTitle") : t("emptyTitle")}
          </h3>
          <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
            {hasFilters
              ? t("emptyFilteredDescription")
              : t("emptyDescription")}
          </p>
        </div>
      ) : view === "map" ? (
        <div className="space-y-2">
          <div className="h-[480px]">
            <LeadsMap
              markers={markers}
              onMarkerClick={openLead}
              className="h-full"
            />
          </div>
          {markers.length < leads.length && (
            <p className="text-xs text-muted-foreground">
              {t("mapMissingLocation", {
                missing: leads.length - markers.length,
                total: leads.length,
              })}
            </p>
          )}
        </div>
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("columns.name")}</TableHead>
                <TableHead>{t("columns.address")}</TableHead>
                <TableHead>{t("columns.phone")}</TableHead>
                <TableHead>{t("columns.website")}</TableHead>
                <TableHead>{t("columns.category")}</TableHead>
                <TableHead>{t("columns.status")}</TableHead>
                <TableHead className="text-right">
                  {t("columns.dateSaved")}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {leads.map((lead) => {
                const href = safeHref(lead.website)
                return (
                  <TableRow
                    key={lead.id}
                    className="cursor-pointer"
                    onClick={() => openLead(lead.id)}
                  >
                    <TableCell className="font-medium">{lead.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {lead.address ?? "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {lead.phone ?? "—"}
                    </TableCell>
                    <TableCell className="max-w-[220px] truncate text-muted-foreground">
                      {lead.website ? (
                        href ? (
                          <a
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline"
                            onClick={(event) => event.stopPropagation()}
                          >
                            {lead.website}
                          </a>
                        ) : (
                          lead.website
                        )
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {lead.category ?? "—"}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={lead.status} />
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground tabular-nums">
                      {formatDate(lead.createdAt)}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
