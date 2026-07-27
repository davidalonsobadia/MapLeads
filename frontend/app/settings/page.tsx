"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Loader2 } from "lucide-react"
import { useTranslations } from "next-intl"
import { config } from "@/lib/config"
import { authApi } from "@/features/auth/api"
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

/**
 * Profile settings tab: edit and save the current user's name. Pre-fills from
 * /api/auth/me and persists via PATCH /api/auth/me, surfacing loading, success
 * and error states while keeping submit disabled during a save.
 */
export default function ProfileSettingsPage() {
  const router = useRouter()
  const t = useTranslations("settings.profile")
  const [name, setName] = useState("")
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    let active = true

    const load = async () => {
      try {
        const result = await authApi.getCurrentUser()
        if (!result.success) {
          router.push(config.routes.login)
          return
        }
        if (active) setName(result.user?.name ?? "")
      } catch (error) {
        console.error("[MapLeads] Load profile error:", error)
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

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      setSaveError(t("nameRequired"))
      setSaved(false)
      return
    }

    setSaving(true)
    setSaveError(null)
    setSaved(false)
    try {
      const result = await authApi.updateProfile({ name: trimmed })
      if (result.success) {
        setName(result.user?.name ?? trimmed)
        setSaved(true)
      } else {
        setSaveError(result.message || t("saveError"))
      }
    } catch (error) {
      console.error("[MapLeads] Update profile error:", error)
      setSaveError(t("saveError"))
    } finally {
      setSaving(false)
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
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="profile-name">{t("nameLabel")}</Label>
              <Input
                id="profile-name"
                value={name}
                onChange={(event) => {
                  setName(event.target.value)
                  setSaved(false)
                  setSaveError(null)
                }}
                placeholder={t("namePlaceholder")}
                disabled={saving}
              />
            </div>

            {saveError && (
              <p className="text-sm text-destructive">{saveError}</p>
            )}
            {saved && (
              <p className="text-sm text-emerald-600 dark:text-emerald-400">
                {t("success")}
              </p>
            )}

            <Button type="submit" disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {saving ? t("saving") : t("save")}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  )
}
