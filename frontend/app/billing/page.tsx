"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, Loader2, MapPin } from "lucide-react"
import { config } from "@/lib/config"
import { authApi } from "@/features/auth/api"
import { billingApi } from "@/features/billing/api"
import { TrialBanner } from "@/features/billing/trial-banner"
import { UsageCard } from "@/features/billing/usage-card"
import { PlanSummaryCard } from "@/features/billing/plan-summary-card"
import { ChangePlanCard } from "@/features/billing/change-plan-card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import type { SubscriptionUsage } from "@/lib/types"

export default function BillingPage() {
  const router = useRouter()
  const [subscription, setSubscription] = useState<SubscriptionUsage | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [pendingPlan, setPendingPlan] = useState<string | null>(null)
  const [managing, setManaging] = useState(false)

  useEffect(() => {
    let active = true

    const load = async () => {
      try {
        const userResult = await authApi.getCurrentUser()
        if (!userResult.success) {
          router.push(config.routes.login)
          return
        }

        const result = await billingApi.getSubscription()
        if (!active) return

        if (result.success && result.subscription) {
          setSubscription(result.subscription)
        } else {
          setLoadError(result.message || "Failed to load your subscription.")
        }
      } catch (error) {
        console.error("[MapLeads] Load billing error:", error)
        if (active) setLoadError("Failed to load your subscription.")
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    return () => {
      active = false
    }
  }, [router])

  const handleChoosePlan = async (plan: string) => {
    setActionError(null)
    setPendingPlan(plan)
    try {
      const result = await billingApi.createCheckoutSession(plan)
      if (result.success && result.url) {
        window.location.href = result.url
        return
      }
      setActionError(result.message || "Failed to start checkout.")
    } catch (error) {
      console.error("[MapLeads] Checkout error:", error)
      setActionError("Failed to start checkout.")
    } finally {
      setPendingPlan(null)
    }
  }

  const handleManage = async () => {
    setActionError(null)
    setManaging(true)
    try {
      const result = await billingApi.createPortalSession()
      if (result.success && result.url) {
        window.location.href = result.url
        return
      }
      setActionError(result.message || "Failed to open the billing portal.")
    } catch (error) {
      console.error("[MapLeads] Portal error:", error)
      setActionError("Failed to open the billing portal.")
    } finally {
      setManaging(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto flex items-center justify-between px-4 py-4">
          <Link href={config.routes.dashboard} className="flex items-center gap-2">
            <MapPin className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">MapLeads</span>
          </Link>
          <Button variant="ghost" size="sm" asChild>
            <Link href={config.routes.dashboard}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to dashboard
            </Link>
          </Button>
        </div>
      </header>

      <main className="container mx-auto max-w-4xl space-y-6 px-4 py-8">
        <div>
          <h1 className="text-2xl font-semibold">Billing</h1>
          <p className="text-sm text-muted-foreground">
            Manage your plan, review this month&apos;s usage and update payment
            details.
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : loadError || !subscription ? (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {loadError || "Subscription unavailable."}
          </div>
        ) : (
          <>
            <TrialBanner subscription={subscription} />

            {subscription.status === "trialing" && (
              <Alert>
                <AlertTitle>No credit card required</AlertTitle>
                <AlertDescription>
                  Your free trial doesn&apos;t need a card. You only need to add
                  one when you choose a paid plan below.
                </AlertDescription>
              </Alert>
            )}

            {actionError && (
              <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {actionError}
              </div>
            )}

            <div className="grid gap-4 md:grid-cols-2">
              <PlanSummaryCard
                subscription={subscription}
                onManage={handleManage}
                managing={managing}
              />
              <UsageCard subscription={subscription} />
            </div>

            <ChangePlanCard
              subscription={subscription}
              onChoosePlan={handleChoosePlan}
              pendingPlan={pendingPlan}
            />
          </>
        )}
      </main>
    </div>
  )
}
