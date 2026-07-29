"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { LogOut, MapPin, Settings } from "lucide-react"
import { useTranslations } from "next-intl"
import { config } from "@/lib/config"
import { authApi } from "@/features/auth/api"
import { Button } from "@/components/ui/button"

interface AppHeaderProps {
  /** Display name of the signed-in user, shown in the welcome greeting. */
  userName?: string
}

/**
 * Shared authenticated header: MapLeads home link plus the account action area
 * (welcome greeting, Settings and Logout). Used by the dashboard and settings
 * pages so the header stays in a single place. Billing lives under the
 * Settings tabs, not here, to avoid a duplicate entry point.
 */
export function AppHeader({ userName }: AppHeaderProps) {
  const router = useRouter()
  const t = useTranslations("header")

  const handleLogout = async () => {
    await authApi.logout()
    router.push(config.routes.login)
  }

  return (
    <header className="border-b bg-card">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link href={config.routes.dashboard} className="flex items-center gap-2">
            <MapPin className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">{config.app.name}</span>
          </Link>
          <div className="flex items-center gap-4">
            {userName && (
              <span className="text-sm text-muted-foreground">
                {t.rich("welcome", {
                  name: userName,
                  strong: (chunks) => <strong>{chunks}</strong>,
                })}
              </span>
            )}
            <Button variant="ghost" size="sm" asChild>
              <Link href={config.routes.settings}>
                <Settings className="h-4 w-4 mr-2" />
                {t("settings")}
              </Link>
            </Button>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOut className="h-4 w-4 mr-2" />
              {t("logout")}
            </Button>
          </div>
        </div>
      </div>
    </header>
  )
}
