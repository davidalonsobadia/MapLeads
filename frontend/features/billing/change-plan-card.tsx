"use client"

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
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Change plan</CardTitle>
        <CardDescription>
          Pick a plan to continue on Stripe&apos;s secure checkout. A card is only
          required to move onto a paid plan.
        </CardDescription>
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
                      Current
                    </span>
                  )}
                </div>
                <p className="text-2xl font-bold">
                  €{plan.priceEur}
                  <span className="text-sm font-normal text-muted-foreground">
                    {" "}
                    /mo
                  </span>
                </p>
                <p className="text-sm text-muted-foreground">
                  {plan.monthlyLeadQuota.toLocaleString()} leads / month
                </p>
                <p className="text-sm text-muted-foreground">{plan.description}</p>
              </div>
              <Button
                className="mt-auto"
                variant={isCurrent ? "outline" : "default"}
                disabled={isCurrent || pendingPlan !== null}
                onClick={() => onChoosePlan(plan.id)}
              >
                {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isCurrent ? "Current plan" : "Choose plan"}
              </Button>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
