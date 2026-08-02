"use client"

import { useRouter } from "next/navigation"
import { useLocale } from "next-intl"
import { isLocale, locales, type Locale } from "@/i18n/routing"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

// One year, mirroring the NEXT_LOCALE lifetime set elsewhere in the app.
const LOCALE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365

// Endonyms — each language's own name, so the labels are locale-independent
// and need no message keys.
const LOCALE_LABELS: Record<Locale, string> = {
  en: "English",
  es: "Español",
}

/** Update the client-readable NEXT_LOCALE cookie so next-intl picks up the change. */
function setLocaleCookie(locale: Locale) {
  document.cookie = `NEXT_LOCALE=${locale}; path=/; max-age=${LOCALE_COOKIE_MAX_AGE}; samesite=lax`
}

/**
 * Language switcher for anonymous visitors on the public landing page.
 * Reflects the active locale via `useLocale()` and, on change, persists the
 * choice in the NEXT_LOCALE cookie (client-side only — no backend call) and
 * refreshes so server components re-render with the new locale's messages.
 */
export function LocaleSwitcher() {
  const router = useRouter()
  const locale = useLocale()

  const handleChange = (value: string) => {
    if (!isLocale(value) || value === locale) return
    setLocaleCookie(value)
    router.refresh()
  }

  return (
    <Select value={locale} onValueChange={handleChange}>
      <SelectTrigger className="w-32" aria-label="Language">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {locales.map((option) => (
          <SelectItem key={option} value={option}>
            {LOCALE_LABELS[option]}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
