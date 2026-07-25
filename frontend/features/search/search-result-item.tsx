"use client"

// A single row in the search-results list (#20).
//
// Presentational: it renders one result's details (name, category, address,
// phone, website), a selection checkbox, and — for results already in the
// project — an "Already in your list" marker instead of a checkbox. Hover and
// active state are controlled by the parent so the row and its map pin stay in
// sync both ways.

import { Check, Globe, MapPin, Phone, Tag } from "lucide-react"

import type { SearchResult } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"

interface SearchResultItemProps {
  result: SearchResult
  /** Whether this result is already saved in the project (dedup). */
  saved: boolean
  /** Whether its selection checkbox is checked. */
  selected: boolean
  /** Whether it is the active (map-focused) row. */
  active: boolean
  /** Whether it is the hovered row. */
  hovered: boolean
  onSelectedChange: (checked: boolean) => void
  onHover: (hovered: boolean) => void
  onActivate: () => void
}

export function SearchResultItem({
  result,
  saved,
  selected,
  active,
  hovered,
  onSelectedChange,
  onHover,
  onActivate,
}: SearchResultItemProps) {
  return (
    <div
      className={cn(
        "flex gap-3 rounded-lg border p-3 transition-colors",
        (active || hovered) && "border-primary bg-accent/50",
        saved && "opacity-80",
      )}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      onClick={onActivate}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault()
          onActivate()
        }
      }}
    >
      <div className="pt-0.5" onClick={(event) => event.stopPropagation()}>
        {saved ? (
          <span
            className="flex h-4 w-4 items-center justify-center rounded-sm bg-success text-white"
            aria-label="Already in your list"
          >
            <Check className="h-3 w-3" />
          </span>
        ) : (
          <Checkbox
            checked={selected}
            onCheckedChange={(value) => onSelectedChange(value === true)}
            aria-label={`Select ${result.name ?? "result"}`}
          />
        )}
      </div>

      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="truncate font-medium leading-tight">
            {result.name ?? "Unnamed place"}
          </h3>
          {saved && (
            <Badge
              variant="secondary"
              className="shrink-0 bg-success/15 text-success"
            >
              Already in your list
            </Badge>
          )}
        </div>

        {result.category && (
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Tag className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate">{result.category}</span>
          </p>
        )}

        {result.address && (
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate">{result.address}</span>
          </p>
        )}

        {result.phone && (
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Phone className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate">{result.phone}</span>
          </p>
        )}

        {result.website && (
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Globe className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <a
              href={result.website}
              target="_blank"
              rel="noopener noreferrer"
              className="truncate text-primary hover:underline"
              onClick={(event) => event.stopPropagation()}
            >
              {result.website}
            </a>
          </p>
        )}
      </div>
    </div>
  )
}
