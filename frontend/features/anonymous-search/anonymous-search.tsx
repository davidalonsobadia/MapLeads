"use client"

// Anonymous "try a search" experience (#102).
//
// Client orchestrator for the public /try page. It owns the search lifecycle
// via the client helper (`api.ts`, from #98) and renders, depending on outcome:
//  - the search form (idle / after an error, with the error inline),
//  - a masked results list plus a prominent signup CTA (on "ok"),
//  - a blocked/upsell panel with no further search (on "blocked").
// No phone/website, no saving, no map — identity-only results.

import { useState } from "react"
import { useTranslations } from "next-intl"
import { SearchX } from "lucide-react"

import type { AnonymousSearchResult, SearchRequestPayload } from "@/lib/types"
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

import { anonymousSearchApi } from "./api"
import { AnonymousSearchForm } from "./anonymous-search-form"
import { BlockedPanel } from "./blocked-panel"
import { MaskedResultItem } from "./masked-result-item"
import { SignupCta } from "./signup-cta"

interface OkState {
  results: AnonymousSearchResult[]
  hiddenCount: number
}

export function AnonymousSearch() {
  const t = useTranslations("anonymousSearch")

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [blocked, setBlocked] = useState(false)
  const [ok, setOk] = useState<OkState | null>(null)

  const handleSearch = async (payload: SearchRequestPayload) => {
    if (submitting) return
    setSubmitting(true)
    setError(null)

    const outcome = await anonymousSearchApi.run(payload)

    if (outcome.status === "ok") {
      setOk({ results: outcome.results, hiddenCount: outcome.hiddenCount })
    } else if (outcome.status === "blocked") {
      setOk(null)
      setBlocked(true)
    } else {
      setError(outcome.message || t("errors.runFailed"))
    }

    setSubmitting(false)
  }

  if (blocked) {
    return <BlockedPanel />
  }

  return (
    <div className="space-y-6">
      <AnonymousSearchForm
        onSearch={handleSearch}
        submitting={submitting}
        error={error}
      />

      {ok && (
        <div className="space-y-4">
          <div className="flex items-baseline justify-between gap-2">
            <h2 className="text-lg font-semibold">{t("results.title")}</h2>
            <span className="text-sm text-muted-foreground">
              {t("results.count", { count: ok.results.length })}
            </span>
          </div>

          {ok.results.length === 0 ? (
            <Card>
              <CardHeader className="items-center text-center">
                <span className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
                  <SearchX
                    className="h-6 w-6 text-muted-foreground"
                    aria-hidden="true"
                  />
                </span>
                <CardTitle>{t("results.empty.title")}</CardTitle>
                <CardDescription>
                  {t("results.empty.description")}
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">
                {t("results.maskedNotice")}
              </p>
              <div className="space-y-2">
                {ok.results.map((result) => (
                  <MaskedResultItem key={result.placeId} result={result} />
                ))}
              </div>
              <SignupCta hiddenCount={ok.hiddenCount} />
            </>
          )}
        </div>
      )}
    </div>
  )
}
