import { cookies } from "next/headers"
import { getRequestConfig } from "next-intl/server"

import { defaultLocale, isLocale, type Locale } from "./routing"

// next-intl request configuration. Runs on every request for server components.
// The active locale comes from the `NEXT_LOCALE` cookie (no locale routing); when
// the cookie is absent or unsupported we fall back to the default locale.
export default getRequestConfig(async () => {
  const cookieStore = await cookies()
  const cookieLocale = cookieStore.get("NEXT_LOCALE")?.value
  const locale: Locale = isLocale(cookieLocale) ? cookieLocale : defaultLocale

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  }
})
