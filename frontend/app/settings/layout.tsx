"use client"

import type React from "react"
import { useEffect, useState } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { Loader2 } from "lucide-react"
import { useTranslations } from "next-intl"
import { config } from "@/lib/config"
import { authApi } from "@/features/auth/api"
import { AppHeader } from "@/components/app-header"
import { cn } from "@/lib/utils"

const TABS = [
  { key: "profile", href: "/settings" },
  { key: "billing", href: "/settings/billing" },
  { key: "preferences", href: "/settings/preferences" },
] as const

/**
 * Shared shell for the /settings area: authenticated header plus tabbed
 * navigation (Profile, Billing, Preferences). Guards the whole area by
 * redirecting unauthenticated users to login, mirroring the dashboard/billing
 * pages. Each tab is a route so #62/#63 can fill Billing/Preferences later.
 */
export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()
  const t = useTranslations("settings")
  const [userName, setUserName] = useState<string | undefined>(undefined)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    const load = async () => {
      try {
        const result = await authApi.getCurrentUser()
        if (!result.success) {
          router.push(config.routes.login)
          return
        }
        if (active) setUserName(result.user?.name)
      } catch (error) {
        console.error("[MapLeads] Load settings user error:", error)
        router.push(config.routes.login)
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    return () => {
      active = false
    }
  }, [router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  const isActive = (href: string) =>
    href === "/settings" ? pathname === href : pathname.startsWith(href)

  return (
    <div className="min-h-screen bg-background">
      <AppHeader userName={userName} />

      <main className="container mx-auto max-w-4xl space-y-6 px-4 py-8">
        <div>
          <h1 className="text-2xl font-semibold">{t("title")}</h1>
          <p className="text-sm text-muted-foreground">{t("description")}</p>
        </div>

        <nav className="inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground">
          {TABS.map((tab) => (
            <Link
              key={tab.key}
              href={tab.href}
              aria-current={isActive(tab.href) ? "page" : undefined}
              className={cn(
                "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                isActive(tab.href)
                  ? "bg-background text-foreground shadow-sm"
                  : "hover:text-foreground",
              )}
            >
              {t(`tabs.${tab.key}`)}
            </Link>
          ))}
        </nav>

        {children}
      </main>
    </div>
  )
}
