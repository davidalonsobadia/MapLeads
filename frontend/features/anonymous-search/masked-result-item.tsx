"use client"

// A single row in the masked anonymous-results list (#102).
//
// Reuses the visual language of `features/search/search-result-item.tsx`
// (bordered row, lucide icons) but shows identity only — name, category,
// address — with no phone/website, no selection checkbox, and no map. A locked
// "contact details hidden" hint teases the fields that require an account.

import { useTranslations } from "next-intl"
import { Lock, MapPin, Tag } from "lucide-react"

import type { AnonymousSearchResult } from "@/lib/types"
import { formatCategory } from "@/lib/utils"

interface MaskedResultItemProps {
  result: AnonymousSearchResult
}

export function MaskedResultItem({ result }: MaskedResultItemProps) {
  const t = useTranslations("anonymousSearch.item")
  const category = formatCategory(result.category)

  return (
    <div className="flex flex-col gap-1 rounded-lg border p-3">
      <h3 className="truncate font-medium leading-tight">
        {result.name ?? t("unnamed")}
      </h3>

      {category && (
        <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Tag className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span className="truncate">{category}</span>
        </p>
      )}

      {result.address && (
        <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span className="truncate">{result.address}</span>
        </p>
      )}

      <p className="flex items-center gap-1.5 text-sm text-muted-foreground/80">
        <Lock className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span className="truncate italic">{t("contactHidden")}</span>
      </p>
    </div>
  )
}
