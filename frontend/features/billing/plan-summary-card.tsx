"use client"

import { CreditCard, Loader2 } from "lucide-react"
import type { SubscriptionUsage } from "@/lib/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

interface PlanSummaryCardProps {
  subscription: SubscriptionUsage
  onManage: () => void
  managing: boolean
}

function formatDate(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

const STATUS_LABELS: Record<string, string> = {
  trialing: "Trial",
  active: "Active",
  past_due: "Past due",
  canceled: "Canceled",
}

/**
 * Current subscription summary: plan name, status and the renewal (or trial
 * end) date, plus the "Manage / cancel" action that opens the Stripe Billing
 * Portal.
 */
export function PlanSummaryCard({
  subscription,
  onManage,
  managing,
}: PlanSummaryCardProps) {
  const { plan, status, periodEnd } = subscription
  const renewsOn = formatDate(periodEnd)
  const statusLabel = STATUS_LABELS[status] ?? status

  const dateLabel =
    status === "trialing"
      ? "Trial ends on"
      : status === "canceled"
        ? "Access ends on"
        : "Renews on"

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <CreditCard className="h-4 w-4 text-primary" />
          Current plan
        </CardTitle>
        <CardDescription className="text-lg font-semibold capitalize text-foreground">
          {plan}
        </CardDescription>
        <CardAction>
          <Badge
            variant={status === "past_due" ? "destructive" : "secondary"}
          >
            {statusLabel}
          </Badge>
        </CardAction>
      </CardHeader>
      <CardContent>
        {renewsOn ? (
          <p className="text-sm text-muted-foreground">
            {dateLabel} <span className="font-medium text-foreground">{renewsOn}</span>
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">
            No renewal date available.
          </p>
        )}
      </CardContent>
      <CardFooter>
        <Button variant="outline" onClick={onManage} disabled={managing}>
          {managing ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <CreditCard className="mr-2 h-4 w-4" />
          )}
          Manage / cancel
        </Button>
      </CardFooter>
    </Card>
  )
}
