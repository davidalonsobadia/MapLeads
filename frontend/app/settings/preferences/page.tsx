"use client"

import { useTranslations } from "next-intl"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

/**
 * Preferences settings tab placeholder. Filled by #63; kept here so the tab is
 * a reachable navigation target within the settings shell.
 */
export default function PreferencesSettingsPage() {
  const t = useTranslations("settings.preferences")

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{t("placeholder")}</p>
      </CardContent>
    </Card>
  )
}
