"use client"

// Shared Google Maps component for MapLeads.
//
// A presentational, reusable map used by the search-results map and the
// saved-leads map overlay. It knows nothing about search or leads logic — it
// just renders a set of markers, colors each pin by lead status (see
// `lib/lead-status.ts`), supports controlled hover/selection highlighting, and
// fires a callback when a marker is clicked.
//
// Rendering relies on `@vis.gl/react-google-maps`. The Google Maps JavaScript
// API key is read from `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`; when it is absent the
// component renders a friendly message instead of crashing.

import { useEffect, useMemo } from "react"
import {
  APIProvider,
  AdvancedMarker,
  Map as GoogleMap,
  Pin,
  useMap,
} from "@vis.gl/react-google-maps"
import { MapPinOff } from "lucide-react"

import { getLeadStatusStyle, type LeadStatus } from "@/lib/lead-status"
import { cn } from "@/lib/utils"

export interface LeadMarker {
  /** Stable identifier, used for hover/selection and click callbacks. */
  id: string
  lat: number
  lng: number
  /** Optional label rendered as the marker title (native tooltip). */
  label?: string
  /** Lead status; drives the pin color. Defaults to `new` when omitted. */
  status?: LeadStatus | string
}

export interface LeadsMapProps {
  /** Markers to render. */
  markers?: LeadMarker[]
  /** Id of the externally hovered marker (controlled highlight). */
  hoveredId?: string | null
  /** Id of the externally selected marker (controlled highlight). */
  selectedId?: string | null
  /** Called with a marker id when its pin is clicked. */
  onMarkerClick?: (id: string) => void
  /**
   * Called when a marker is hovered (its id) or unhovered (`null`).
   * Lets a parent keep hover state in sync with, e.g., a results list.
   */
  onMarkerHover?: (id: string | null) => void
  /** Explicit center. When omitted, the map fits all markers. */
  center?: { lat: number; lng: number }
  /** Initial zoom level. Defaults to 12. */
  zoom?: number
  /**
   * Google Maps API key. Defaults to `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`.
   * Exposed as a prop mainly for testing/storybook.
   */
  apiKey?: string
  /**
   * Cloud-based map style id. Required by Google for Advanced Markers; defaults
   * to `NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID`, falling back to Google's demo id.
   */
  mapId?: string
  className?: string
}

// Fallback center (roughly central Europe) used only when there are no markers
// and no explicit center — keeps the map from rendering on null island.
const DEFAULT_CENTER = { lat: 40.4168, lng: -3.7038 }
const DEFAULT_ZOOM = 12

// Brand blue (#1A73E8) used as the active/highlight ring around a pin.
const HIGHLIGHT_COLOR = "#1a73e8"

/**
 * Fits the map viewport to the given markers whenever they change, unless an
 * explicit center is provided. Rendered as a child so it can use `useMap`.
 */
function FitBounds({
  markers,
  disabled,
}: {
  markers: LeadMarker[]
  disabled: boolean
}) {
  const map = useMap()

  useEffect(() => {
    if (disabled || !map || markers.length === 0) return
    if (markers.length === 1) {
      map.setCenter({ lat: markers[0].lat, lng: markers[0].lng })
      return
    }
    // Build a bounds literal (avoids depending on the `google` global) that
    // wraps every marker, then let the map fit its viewport to it.
    const bounds = markers.reduce(
      (acc, m) => ({
        north: Math.max(acc.north, m.lat),
        south: Math.min(acc.south, m.lat),
        east: Math.max(acc.east, m.lng),
        west: Math.min(acc.west, m.lng),
      }),
      {
        north: markers[0].lat,
        south: markers[0].lat,
        east: markers[0].lng,
        west: markers[0].lng,
      },
    )
    map.fitBounds(bounds, 64)
  }, [map, markers, disabled])

  return null
}

function NoKeyState({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex h-full w-full flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border bg-muted p-6 text-center",
        className,
      )}
      role="status"
    >
      <MapPinOff className="size-6 text-muted-foreground" aria-hidden="true" />
      <p className="text-sm font-medium text-foreground">Map unavailable</p>
      <p className="max-w-xs text-xs text-muted-foreground">
        Set <code className="font-mono">NEXT_PUBLIC_GOOGLE_MAPS_API_KEY</code> to
        display the map.
      </p>
    </div>
  )
}

export function LeadsMap({
  markers = [],
  hoveredId = null,
  selectedId = null,
  onMarkerClick,
  onMarkerHover,
  center,
  zoom = DEFAULT_ZOOM,
  apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY,
  mapId = process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID ?? "DEMO_MAP_ID",
  className,
}: LeadsMapProps) {
  const defaultCenter = useMemo(() => {
    if (center) return center
    if (markers.length > 0) {
      const sum = markers.reduce(
        (acc, m) => ({ lat: acc.lat + m.lat, lng: acc.lng + m.lng }),
        { lat: 0, lng: 0 },
      )
      return { lat: sum.lat / markers.length, lng: sum.lng / markers.length }
    }
    return DEFAULT_CENTER
  }, [center, markers])

  if (!apiKey) {
    return <NoKeyState className={className} />
  }

  return (
    <div className={cn("h-full w-full overflow-hidden rounded-md", className)}>
      <APIProvider apiKey={apiKey}>
        <GoogleMap
          mapId={mapId}
          defaultCenter={defaultCenter}
          defaultZoom={zoom}
          gestureHandling="greedy"
          disableDefaultUI={false}
          className="h-full w-full"
        >
          <FitBounds markers={markers} disabled={Boolean(center)} />
          {markers.map((marker) => {
            const style = getLeadStatusStyle(marker.status ?? "new")
            const isActive =
              marker.id === hoveredId || marker.id === selectedId
            return (
              <AdvancedMarker
                key={marker.id}
                position={{ lat: marker.lat, lng: marker.lng }}
                title={marker.label}
                zIndex={isActive ? 1000 : undefined}
                onClick={() => onMarkerClick?.(marker.id)}
                onMouseEnter={() => onMarkerHover?.(marker.id)}
                onMouseLeave={() => onMarkerHover?.(null)}
              >
                <Pin
                  background={style.hex}
                  borderColor={isActive ? HIGHLIGHT_COLOR : style.hex}
                  glyphColor="#ffffff"
                  scale={isActive ? 1.4 : 1}
                />
              </AdvancedMarker>
            )
          })}
        </GoogleMap>
      </APIProvider>
    </div>
  )
}

export default LeadsMap
