"use client"

// Signup call-to-action shown alongside anonymous results (#102).
//
// Teases the hidden results (via `hiddenCount`) and the hidden contact details,
// and pushes the visitor to create an account, with a secondary sign-in link.

import Link from "next/link"
import { useTranslations } from "next-intl"
import { Sparkles } from "lucide-react"

import { config } from "@/lib/config"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface SignupCtaProps {
  hiddenCount: number
}

export function SignupCta({ hiddenCount }: SignupCtaProps) {
  const t = useTranslations("anonymousSearch.cta")

  return (
    <Card className="border-primary/50 bg-primary/5">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" aria-hidden="true" />
          {t("title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          {t("hiddenResults", { count: hiddenCount })}
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button asChild>
            <Link href={config.routes.register}>{t("register")}</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href={config.routes.login}>{t("login")}</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
