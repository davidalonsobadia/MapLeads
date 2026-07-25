"use client"

// Point + radius location picker for the new-search screen.
//
// Reuses the shared <LeadsMap> (#15) as a click-to-drop point picker: clicking
// the map sets the search center, and a slider controls the radius in km. A
// circle overlay visualizes the covered area so the point and slider read as a
// single control.

import { useEffect, useMemo } from "react"
import { useMap, useMapsLibrary } from "@vis.gl/react-google-maps"

import { LeadsMap, type LeadMarker } from "@/components/map"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"

export const MIN_RADIUS_KM = 1
export const MAX_RADIUS_KM = 50

// Brand blue (#1A73E8), matching the map highlight ring.
const CIRCLE_COLOR = "#1a73e8"

export interface LatLng {
  lat: number
  lng: number
}

export interface LocationMapPickerProps {
  point: LatLng | null
  onPointChange: (point: LatLng) => void
  radiusKm: number
  onRadiusChange: (radiusKm: number) => void
  disabled?: boolean
}

/**
 * Draws (and keeps in sync) a radius circle around the picked point. Rendered
 * inside <LeadsMap> so it can reach the map instance via `useMap`.
 */
function RadiusCircle({ center, radiusKm }: { center: LatLng; radiusKm: number }) {
  const map = useMap()
  const maps = useMapsLibrary("maps")
  const circle = useMemo(() => {
    if (!maps) return null
    return new maps.Circle({
      strokeColor: CIRCLE_COLOR,
      strokeOpacity: 0.8,
      strokeWeight: 2,
      fillColor: CIRCLE_COLOR,
      fillOpacity: 0.12,
      clickable: false,
    })
  }, [maps])

  useEffect(() => {
    if (!circle || !map) return
    circle.setMap(map)
    circle.setCenter(center)
    circle.setRadius(radiusKm * 1000)
    return () => circle.setMap(null)
  }, [circle, map, center, radiusKm])

  return null
}

export function LocationMapPicker({
  point,
  onPointChange,
  radiusKm,
  onRadiusChange,
  disabled,
}: LocationMapPickerProps) {
  const markers: LeadMarker[] = useMemo(
    () =>
      point
        ? [{ id: "search-point", lat: point.lat, lng: point.lng, label: "Search center" }]
        : [],
    [point],
  )

  return (
    <div className="space-y-4">
      <div className="h-[320px] w-full">
        <LeadsMap
          markers={markers}
          onMapClick={disabled ? undefined : onPointChange}
        >
          {point && <RadiusCircle center={point} radiusKm={radiusKm} />}
        </LeadsMap>
      </div>

      <p className="text-sm text-muted-foreground">
        {point
          ? `Center: ${point.lat.toFixed(4)}, ${point.lng.toFixed(4)}`
          : "Click the map to drop a search point."}
      </p>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="search-radius">Radius</Label>
          <span className="text-sm tabular-nums text-muted-foreground">
            {radiusKm} km
          </span>
        </div>
        <Slider
          id="search-radius"
          min={MIN_RADIUS_KM}
          max={MAX_RADIUS_KM}
          step={1}
          value={[radiusKm]}
          onValueChange={(values) => onRadiusChange(values[0])}
          disabled={disabled || !point}
          aria-label="Search radius in kilometers"
        />
      </div>
    </div>
  )
}
