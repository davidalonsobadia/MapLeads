import { redirect } from "next/navigation"
import { config } from "@/lib/config"

/**
 * Legacy /billing route. Billing now lives inside Settings as the Billing tab,
 * so redirect old bookmarks to the Settings Billing tab. The actual UI lives in
 * app/settings/billing/page.tsx.
 */
export default function BillingPage() {
  redirect(config.routes.billing)
}
