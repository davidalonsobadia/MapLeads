"use client"

// Anonymous "try a search" form (#102).
//
// Modeled on `features/search/new-search-form.tsx` but text-only: a keyword and
// a free-text location, no map/point mode. It deliberately uses a plain <Input>
// for the location (not Google Places Autocomplete) so the public /try page
// stays free of the Google Maps browser key. Submitting hands the payload up to
// the parent, which owns the request lifecycle (loading / error state).

import { useMemo, useState } from "react"
import { useTranslations } from "next-intl"
import { Loader2, Search } from "lucide-react"

import type { SearchRequestPayload } from "@/lib/types"
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

interface AnonymousSearchFormProps {
  onSearch: (payload: SearchRequestPayload) => void
  submitting: boolean
  error: string | null
}

export function AnonymousSearchForm({
  onSearch,
  submitting,
  error,
}: AnonymousSearchFormProps) {
  const t = useTranslations("anonymousSearch.form")

  const [keyword, setKeyword] = useState("")
  const [locationText, setLocationText] = useState("")

  const canSubmit = useMemo(
    () => keyword.trim().length > 0 && locationText.trim().length > 0,
    [keyword, locationText],
  )

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!canSubmit || submitting) return
    onSearch({
      keyword: keyword.trim(),
      location_type: "text",
      location_text: locationText.trim(),
    })
  }

  return (
    <form onSubmit={handleSubmit}>
      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="anon-search-keyword">{t("keywordLabel")}</Label>
            <Input
              id="anon-search-keyword"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder={t("keywordPlaceholder")}
              disabled={submitting}
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="anon-search-location">{t("locationLabel")}</Label>
            <Input
              id="anon-search-location"
              value={locationText}
              onChange={(event) => setLocationText(event.target.value)}
              placeholder={t("locationPlaceholder")}
              disabled={submitting}
            />
            <p className="text-sm text-muted-foreground">{t("locationHint")}</p>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex justify-end">
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
