"use client"

import { useTranslations } from "next-intl"
import { Gauge } from "lucide-react"
import type { SubscriptionUsage } from "@/lib/types"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"

interface UsageCardProps {
  subscription: SubscriptionUsage
}

export function UsageCard({ subscription }: UsageCardProps) {
  const t = useTranslations("billing.usage")
  const { leadsUsed, monthlyLeadQuota, remaining, plan } = subscription
  const percentage =
    monthlyLeadQuota > 0
      ? Math.min(100, Math.round((leadsUsed / monthlyLeadQuota) * 100))
      : 0

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Gauge className="h-4 w-4 text-primary" />
          {t("title")}
        </CardTitle>
        <CardDescription>
          {t("used", {
            used: leadsUsed.toLocaleString(),
            quota: monthlyLeadQuota.toLocaleString(),
          })}
        </CardDescription>
        <CardAction>
          <Badge variant="secondary" className="capitalize">
            {plan}
          </Badge>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-2">
        <Progress
          value={percentage}
          aria-label={t("progressAria", { percentage })}
        />
        <p className="text-sm text-muted-foreground">
          {t("remaining", { remaining })}
        </p>
      </CardContent>
    </Card>
  )
}
