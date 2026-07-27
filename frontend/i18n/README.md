# Frontend i18n (next-intl)

Internationalization scaffolding for the MapLeads frontend. English (`en`) and
Spanish (`es`) are supported. There is **no locale routing** — no `[locale]` URL
segment and no locale-prefix middleware. The active locale is resolved from the
`NEXT_LOCALE` cookie in [`request.ts`](./request.ts), defaulting to `en`.

## Layout

- `i18n/routing.ts` — supported `locales`, `defaultLocale`, and the `isLocale`
  guard. Import these instead of hardcoding locale strings.
- `i18n/request.ts` — next-intl `getRequestConfig`: reads the `NEXT_LOCALE`
  cookie and loads the matching catalog from `messages/`.
- `messages/{en,es}.json` — message catalogs. Keys are grouped by namespace
  (currently just `common`). Later tasks (#64–#66) extract screen strings here.
- The next-intl plugin is wired in `next.config.mjs`; the root
  `app/layout.tsx` sets `<html lang={locale}>` and mounts
  `NextIntlClientProvider`.

## Usage

### Server components (async)

```tsx
import { getTranslations } from "next-intl/server"

export default async function Page() {
  const t = await getTranslations("common")
  return <h1>{t("appName")}</h1>
}
```

### Client components

```tsx
"use client"
import { useTranslations } from "next-intl"

export function SaveButton() {
  const t = useTranslations("common")
  return <button>{t("save")}</button>
}
```

## Switching locale

Set the `NEXT_LOCALE` cookie to `es` (or `en`) and reload. A user-facing language
switcher that writes this cookie is added in a later task (#63); the cookie can be
set manually in the browser devtools to verify translations in the meantime.
