"use client"

import { useTranslations } from "next-intl"
import { Clock } from "lucide-react"
import type { SubscriptionUsage } from "@/lib/types"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

interface TrialBannerProps {
  subscription: SubscriptionUsage
}

/**
 * Trial notice shown only while the subscription is in the trialing state.
 * Renders nothing for any other status.
 */
export function TrialBanner({ subscription }: TrialBannerProps) {
  const t = useTranslations("billing.trial")

  if (subscription.status !== "trialing") {
    return null
  }

  const daysLeft = Math.max(0, subscription.trialDaysLeft)

  return (
    <Alert>
      <Clock className="h-4 w-4" />
      <AlertTitle>
        {daysLeft === 0 ? t("endsToday") : t("daysLeft", { days: daysLeft })}
      </AlertTitle>
      <AlertDescription>{t("description")}</AlertDescription>
    </Alert>
  )
}
