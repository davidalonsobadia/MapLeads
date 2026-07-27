"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Loader2 } from "lucide-react"
import { useTranslations } from "next-intl"
import { useTheme } from "next-themes"
import { config } from "@/lib/config"
import { authApi } from "@/features/auth/api"
import { locales, type Locale } from "@/i18n/routing"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const THEMES = ["light", "dark", "system"] as const

// One year, mirroring the NEXT_LOCALE lifetime set by the /api/auth/me route.
const LOCALE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365

/** Update the client-readable NEXT_LOCALE cookie so next-intl picks up the change. */
function setLocaleCookie(locale: Locale) {
  document.cookie = `NEXT_LOCALE=${locale}; path=/; max-age=${LOCALE_COOKIE_MAX_AGE}; samesite=lax`
}

/**
 * Preferences settings tab: switch the interface language (persisted via
 * PATCH /api/auth/me and reflected in the NEXT_LOCALE cookie for a live change)
 * and toggle the light/dark/system theme (persisted by next-themes in
 * localStorage, no backend field).
 */
export default function PreferencesSettingsPage() {
  const router = useRouter()
  const t = useTranslations("settings.preferences")
  const { theme, setTheme } = useTheme()

  const [language, setLanguage] = useState<Locale | undefined>(undefined)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [savingLanguage, setSavingLanguage] = useState(false)
  const [languageError, setLanguageError] = useState<string | null>(null)

  // next-themes only knows the resolved theme after mount; gate the theme
  // control until then to avoid a hydration mismatch.
  const [mounted, setMounted] = useState(false)
  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    let active = true

    const load = async () => {
      try {
        const result = await authApi.getCurrentUser()
        if (!result.success) {
          router.push(config.routes.login)
          return
        }
        if (active) {
          const current = result.user?.language
          setLanguage(
            (locales as readonly string[]).includes(current)
              ? (current as Locale)
              : "en",
          )
        }
      } catch (error) {
        console.error("[MapLeads] Load preferences error:", error)
        if (active) setLoadError(t("loadError"))
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    return () => {
      active = false
    }
  }, [router, t])

  const handleLanguageChange = async (value: string) => {
    if (!(locales as readonly string[]).includes(value)) return
    const next = value as Locale
    const previous = language

    setLanguage(next)
    setSavingLanguage(true)
    setLanguageError(null)
    try {
      const result = await authApi.updateProfile({ language: next })
      if (result.success) {
        setLocaleCookie(next)
        // Re-render server components with the new locale's messages.
        router.refresh()
      } else {
        setLanguage(previous)
        setLanguageError(result.message || t("language.saveError"))
      }
    } catch (error) {
      console.error("[MapLeads] Update language error:", error)
      setLanguage(previous)
      setLanguageError(t("language.saveError"))
    } finally {
      setSavingLanguage(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : loadError ? (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {loadError}
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid gap-2">
              <Label htmlFor="preferences-language">
                {t("language.label")}
              </Label>
              <p className="text-sm text-muted-foreground">
                {t("language.description")}
              </p>
              <div className="flex items-center gap-2">
                <Select
                  value={language}
                  onValueChange={handleLanguageChange}
                  disabled={savingLanguage}
                >
                  <SelectTrigger
                    id="preferences-language"
                    className="w-56"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {locales.map((locale) => (
                      <SelectItem key={locale} value={locale}>
                        {t(`language.options.${locale}`)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {savingLanguage && (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                )}
              </div>
              {languageError && (
                <p className="text-sm text-destructive">{languageError}</p>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="preferences-theme">{t("theme.label")}</Label>
              <p className="text-sm text-muted-foreground">
                {t("theme.description")}
              </p>
              <Select
                value={mounted ? theme : undefined}
                onValueChange={setTheme}
                disabled={!mounted}
              >
                <SelectTrigger id="preferences-theme" className="w-56">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {THEMES.map((option) => (
                    <SelectItem key={option} value={option}>
                      {t(`theme.options.${option}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
