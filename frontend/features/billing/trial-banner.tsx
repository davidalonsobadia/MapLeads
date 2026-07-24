"use client"

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
  if (subscription.status !== "trialing") {
    return null
  }

  const daysLeft = Math.max(0, subscription.trialDaysLeft)

  return (
    <Alert>
      <Clock className="h-4 w-4" />
      <AlertTitle>
        {daysLeft === 0
          ? "Your free trial ends today"
          : `${daysLeft} ${daysLeft === 1 ? "day" : "days"} left in your free trial`}
      </AlertTitle>
      <AlertDescription>
        Enjoy full access during your trial. Upgrade any time to keep saving leads without
        interruption.
      </AlertDescription>
    </Alert>
  )
}
