// Shared i18n constants. We do NOT use next-intl's locale routing (no `[locale]`
// URL segment and no locale-prefix middleware); the active locale is resolved from
// the `NEXT_LOCALE` cookie in `./request.ts`.

export const locales = ["en", "es"] as const

export type Locale = (typeof locales)[number]

export const defaultLocale: Locale = "en"

/** Narrow an arbitrary string (e.g. a cookie value) to a supported `Locale`. */
export function isLocale(value: string | undefined | null): value is Locale {
  return value != null && (locales as readonly string[]).includes(value)
}
