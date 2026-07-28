"use client"

import { useState } from "react"
import { useTranslations } from "next-intl"
import { Loader2, Ticket } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { billingApi } from "./api"

interface RedeemCodeCardProps {
  /** Called after a successful redemption so the parent can refresh the plan/usage cards. */
  onRedeemed: () => void
}

/**
 * "Redeem a code" card for the billing settings screen. Submits a promo code to
 * the redeem route handler, shows the backend success/error message inline, and
 * asks the parent to reload the subscription on success so the plan/usage cards
 * reflect the newly granted benefit.
 */
export function RedeemCodeCard({ onRedeemed }: RedeemCodeCardProps) {
  const t = useTranslations("billing.redeem")
  const [code, setCode] = useState("")
  const [pending, setPending] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = code.trim()
    if (!trimmed || pending) return

    setPending(true)
    setSuccess(null)
    setError(null)

    try {
      const result = await billingApi.redeemCode(trimmed)
      if (result.success) {
        setSuccess(result.message || t("success"))
        setCode("")
        onRedeemed()
      } else {
        setError(result.message || t("error"))
      }
    } catch (err) {
      console.error("[MapLeads] Redeem code error:", err)
      setError(t("error"))
    } finally {
      setPending(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Ticket className="h-4 w-4 text-primary" />
          {t("title")}
        </CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
          <Input
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder={t("placeholder")}
            aria-label={t("label")}
            disabled={pending}
            className="sm:flex-1"
          />
          <Button type="submit" disabled={pending || code.trim().length === 0}>
            {pending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t("submit")}
          </Button>
        </form>

        {success && (
          <Alert>
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}
