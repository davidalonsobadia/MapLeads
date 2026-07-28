"use client"

// New-search form: keyword + location (two modes) → run search → results (#20).
//
// Location modes (PRD sec. 4.3):
//  - "text":  free-text location with Google Places Autocomplete.
//  - "point": a point dropped on the map plus a radius slider in km.
// On submit it POSTs to /api/projects/{id}/searches, stashes the returned run
// for the results screen, and navigates there with the new search id.

import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { Loader2, Search } from "lucide-react"

import type { SearchRequestPayload } from "@/lib/types"
import { config } from "@/lib/config"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { searchApi, stashSearchRun } from "./api"
import { PlacesAutocomplete } from "./places-autocomplete"
import { LocationMapPicker, type LatLng } from "./location-map-picker"

type LocationMode = "text" | "point"

const DEFAULT_RADIUS_KM = 10

interface NewSearchFormProps {
  projectId: string
}

export function NewSearchForm({ projectId }: NewSearchFormProps) {
  const router = useRouter()
  const t = useTranslations("search")

  const [keyword, setKeyword] = useState("")
  const [mode, setMode] = useState<LocationMode>("text")
  const [locationText, setLocationText] = useState("")
  const [point, setPoint] = useState<LatLng | null>(null)
  const [radiusKm, setRadiusKm] = useState(DEFAULT_RADIUS_KM)

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = useMemo(() => {
    if (!keyword.trim()) return false
    if (mode === "text") return locationText.trim().length > 0
    return point !== null && radiusKm > 0
  }, [keyword, mode, locationText, point, radiusKm])

  const buildPayload = (): SearchRequestPayload => {
    if (mode === "text") {
      return {
        keyword: keyword.trim(),
        location_type: "text",
        location_text: locationText.trim(),
      }
    }
    return {
      keyword: keyword.trim(),
      location_type: "point",
      lat: point!.lat,
      lng: point!.lng,
      radius_km: radiusKm,
    }
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!canSubmit || submitting) return

    setSubmitting(true)
    setError(null)
    try {
      const result = await searchApi.run(projectId, buildPayload())
      if (!result.success || !result.run) {
        setError(result.message || t("errors.runFailed"))
        return
      }
      stashSearchRun(result.run)
      router.push(config.routes.searchResults(projectId, result.run.searchId))
    } catch {
      setError(t("errors.runFailed"))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>
            {t("description")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="search-keyword">{t("keywordLabel")}</Label>
            <Input
              id="search-keyword"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder={t("keywordPlaceholder")}
              disabled={submitting}
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label>{t("locationLabel")}</Label>
            <Tabs
              value={mode}
              onValueChange={(value) => setMode(value as LocationMode)}
            >
              <TabsList>
                <TabsTrigger value="text" disabled={submitting}>
                  {t("tabs.text")}
                </TabsTrigger>
                <TabsTrigger value="point" disabled={submitting}>
                  {t("tabs.point")}
                </TabsTrigger>
              </TabsList>

              <TabsContent value="text" className="mt-4 space-y-2">
                <PlacesAutocomplete
                  id="search-location-text"
                  value={locationText}
                  onChange={setLocationText}
                  onPlaceSelect={(place) => setLocationText(place.text)}
                  placeholder={t("locationTextPlaceholder")}
                  disabled={submitting}
                />
                <p className="text-sm text-muted-foreground">
                  {t("locationTextHint")}
                </p>
              </TabsContent>

              <TabsContent value="point" className="mt-4">
                <LocationMapPicker
                  point={point}
                  onPointChange={setPoint}
                  radiusKm={radiusKm}
                  onRadiusChange={setRadiusKm}
                  disabled={submitting}
                />
              </TabsContent>
            </Tabs>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button type="submit" disabled={!canSubmit || submitting}>
              {submitting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-2 h-4 w-4" />
              )}
              {t("submit")}
            </Button>
          </div>
        </CardContent>
      </Card>
    </form>
  )
}
