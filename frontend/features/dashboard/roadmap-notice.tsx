"use client"

import { useTranslations } from "next-intl"
import { Linkedin, Sparkles, Send } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

const ITEMS: { key: string; icon: LucideIcon }[] = [
  { key: "linkedin", icon: Linkedin },
  { key: "enrichment", icon: Sparkles },
  { key: "outreach", icon: Send },
]

/**
 * Purely informational notice previewing upcoming product capabilities.
 * No interactivity: no links, buttons, or network requests.
 */
export function RoadmapNotice() {
  const t = useTranslations("dashboard.roadmap")

  return (
    <Card className="bg-muted/40">
      <CardHeader>
        <CardTitle className="text-base">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-3">
        {ITEMS.map(({ key, icon: Icon }) => (
          <div key={key} className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <span className="text-sm font-medium">
                {t(`items.${key}.title`)}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              {t(`items.${key}.description`)}
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
