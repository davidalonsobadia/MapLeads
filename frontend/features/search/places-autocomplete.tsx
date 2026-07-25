"use client"

// Google Places Autocomplete input for the free-text location mode.
//
// Wraps a standard <Input> with Google's classic Places Autocomplete widget so
// the user can pick a city/area (e.g. "Chamberí, Madrid"). When the Google Maps
// JS key is absent it degrades gracefully to a plain text input, mirroring the
// shared <LeadsMap> "no key" behavior — the user can still type a free-text
// location and run a `text` search.

import { useEffect, useRef } from "react"
import { APIProvider, useMapsLibrary } from "@vis.gl/react-google-maps"

import { Input } from "@/components/ui/input"

export interface PlacesAutocompleteProps {
  id?: string
  value: string
  onChange: (value: string) => void
  /**
   * Called when a suggestion is picked, with its resolved coordinates when
   * Google provides geometry. The search still runs as a `text` search; the
   * coordinates are only a convenience for downstream screens.
   */
  onPlaceSelect?: (place: {
    text: string
    lat?: number
    lng?: number
  }) => void
  placeholder?: string
  disabled?: boolean
  apiKey?: string
}

function AutocompleteInput({
  id,
  value,
  onChange,
  onPlaceSelect,
  placeholder,
  disabled,
}: Omit<PlacesAutocompleteProps, "apiKey">) {
  const places = useMapsLibrary("places")
  const inputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    if (!places || !inputRef.current) return

    const autocomplete = new places.Autocomplete(inputRef.current, {
      fields: ["formatted_address", "geometry", "name"],
      types: ["geocode"],
    })

    const listener = autocomplete.addListener("place_changed", () => {
      const place = autocomplete.getPlace()
      const text =
        place.formatted_address || place.name || inputRef.current?.value || ""
      onChange(text)
      onPlaceSelect?.({
        text,
        lat: place.geometry?.location?.lat(),
        lng: place.geometry?.location?.lng(),
      })
    })

    return () => listener.remove()
    // `onChange`/`onPlaceSelect` are treated as stable; re-binding on every
    // render would recreate the widget and drop the dropdown mid-interaction.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [places])

  return (
    <Input
      ref={inputRef}
      id={id}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      autoComplete="off"
    />
  )
}

export function PlacesAutocomplete({
  apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY,
  ...props
}: PlacesAutocompleteProps) {
  if (!apiKey) {
    // No key: fall back to a plain text input so free-text search still works.
    return (
      <Input
        id={props.id}
        value={props.value}
        onChange={(event) => props.onChange(event.target.value)}
        placeholder={props.placeholder}
        disabled={props.disabled}
        autoComplete="off"
      />
    )
  }

  return (
    <APIProvider apiKey={apiKey}>
      <AutocompleteInput {...props} />
    </APIProvider>
  )
}
