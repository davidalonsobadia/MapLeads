"use client"

import { useCallback, useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { useTranslations } from "next-intl"
import { billingApi } from "@/features/billing/api"
import { TrialBanner } from "@/features/billing/trial-banner"
import { UsageCard } from "@/features/billing/usage-card"
import { PlanSummaryCard } from "@/features/billing/plan-summary-card"
import { ChangePlanCard } from "@/features/billing/change-plan-card"
import { RedeemCodeCard } from "@/features/billing/redeem-code-card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import type { SubscriptionUsage } from "@/lib/types"

/**
 * Billing settings tab: renders the plan summary, usage, trial banner and
 * change-plan/portal actions by reusing the billing feature components and
 * billingApi. The surrounding Settings shell provides the authenticated header
 * and auth guard, so this page only owns subscription loading and the checkout
 * and portal actions (moved here from the former standalone /billing page).
 */
export default function BillingSettingsPage() {
  const t = useTranslations("settings.billing")
  const [subscription, setSubscription] = useState<SubscriptionUsage | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [pendingPlan, setPendingPlan] = useState<string | null>(null)
  const [managing, setManaging] = useState(false)

  const loadSubscription = useCallback(async () => {
    try {
      const result = await billingApi.getSubscription()
      if (result.success && result.subscription) {
        setSubscription(result.subscription)
        setLoadError(null)
      } else {
        setLoadError(result.message || t("loadError"))
      }
    } catch (error) {
      console.error("[MapLeads] Load billing error:", error)
      setLoadError(t("loadError"))
    }
  }, [t])

  useEffect(() => {
    let active = true

    const load = async () => {
      if (!active) return
      await loadSubscription()
      if (active) setLoading(false)
    }

    load()
    return () => {
      active = false
    }
  }, [loadSubscription])

  const handleChoosePlan = async (plan: string) => {
    setActionError(null)
    setPendingPlan(plan)
    try {
      const result = await billingApi.createCheckoutSession(plan)
      if (result.success && result.url) {
        window.location.href = result.url
        return
      }
      setActionError(result.message || t("checkoutError"))
    } catch (error) {
      console.error("[MapLeads] Checkout error:", error)
      setActionError(t("checkoutError"))
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
      setActionError(result.message || t("portalError"))
    } catch (error) {
      console.error("[MapLeads] Portal error:", error)
      setActionError(t("portalError"))
    } finally {
      setManaging(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">{t("title")}</h2>
        <p className="text-sm text-muted-foreground">{t("description")}</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : loadError || !subscription ? (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {loadError || t("unavailable")}
        </div>
      ) : (
        <>
          <TrialBanner subscription={subscription} />

          {subscription.status === "trialing" && (
            <Alert>
              <AlertTitle>{t("trialAlertTitle")}</AlertTitle>
              <AlertDescription>{t("trialAlertDescription")}</AlertDescription>
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

          <RedeemCodeCard onRedeemed={loadSubscription} />
        </>
      )}
    </div>
  )
}
