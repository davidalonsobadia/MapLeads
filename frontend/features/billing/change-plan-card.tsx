"use client"

import { useTranslations } from "next-intl"
import { Check, Loader2 } from "lucide-react"
import type { SubscriptionUsage } from "@/lib/types"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { BILLING_PLANS } from "./plans"

interface ChangePlanCardProps {
  subscription: SubscriptionUsage
  onChoosePlan: (planId: string) => void
  pendingPlan: string | null
}

/**
 * Lists the purchasable plans and lets the user start a Stripe Checkout session
 * for any of them. The user's current paid plan is highlighted and its button
 * disabled; every other plan offers a "Choose plan" action.
 */
export function ChangePlanCard({
  subscription,
  onChoosePlan,
  pendingPlan,
}: ChangePlanCardProps) {
  const t = useTranslations("billing.changePlan")

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-3">
        {BILLING_PLANS.map((plan) => {
          const isCurrent = subscription.plan === plan.id
          const isPending = pendingPlan === plan.id

          return (
            <div
              key={plan.id}
              className="flex flex-col gap-3 rounded-lg border p-4"
            >
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{plan.name}</span>
                  {isCurrent && (
                    <span className="flex items-center gap-1 text-xs font-medium text-primary">
                      <Check className="h-3 w-3" />
                      {t("current")}
                    </span>
                  )}
                </div>
                <p className="text-2xl font-bold">
                  €{plan.priceEur}
                  <span className="text-sm font-normal text-muted-foreground">
                    {" "}
                    {t("perMonth")}
                  </span>
                </p>
                <p className="text-sm text-muted-foreground">
                  {t("quota", { quota: plan.monthlyLeadQuota.toLocaleString() })}
                </p>
                <p className="text-sm text-muted-foreground">
                  {t(`plans.${plan.id}.description`)}
                </p>
              </div>
              <Button
                className="mt-auto"
                variant={isCurrent ? "outline" : "default"}
                disabled={isCurrent || pendingPlan !== null}
                onClick={() => onChoosePlan(plan.id)}
              >
                {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isCurrent ? t("currentPlan") : t("choosePlan")}
              </Button>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
