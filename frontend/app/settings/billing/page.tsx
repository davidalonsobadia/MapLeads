"use client"

import { useTranslations } from "next-intl"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

/**
 * Billing settings tab placeholder. Filled by #62; kept here so the tab is a
 * reachable navigation target within the settings shell.
 */
export default function BillingSettingsPage() {
  const t = useTranslations("settings.billing")

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
