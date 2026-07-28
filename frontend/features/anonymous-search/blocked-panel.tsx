"use client"

// Blocked / upsell state for the anonymous "try a search" funnel (#102).
//
// Shown when the client helper returns `{ status: "blocked" }` — the single
// free search is spent. It replaces the form/results with a clear message and a
// signup CTA; no further search is possible from here.

import Link from "next/link"
import { useTranslations } from "next-intl"
import { Lock } from "lucide-react"

import { config } from "@/lib/config"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export function BlockedPanel() {
  const t = useTranslations("anonymousSearch.blocked")

  return (
    <Card className="border-primary/50 bg-primary/5 text-center">
      <CardHeader className="items-center">
        <span className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <Lock className="h-6 w-6 text-primary" aria-hidden="true" />
        </span>
        <CardTitle>{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col justify-center gap-2 sm:flex-row">
        <Button asChild>
          <Link href={config.routes.register}>{t("register")}</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={config.routes.login}>{t("login")}</Link>
        </Button>
      </CardContent>
    </Card>
  )
}
