"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Loader2, Plus, Search } from "lucide-react"
import { useTranslations } from "next-intl"
import { authApi } from "@/features/auth/api"
import { billingApi } from "@/features/billing/api"
import { TrialBanner } from "@/features/billing/trial-banner"
import { UsageCard } from "@/features/billing/usage-card"
import { ProjectsList } from "@/features/projects/projects-list"
import { ProjectDialog } from "@/features/projects/project-dialog"
import { projectsApi } from "@/features/projects/api"
import { DashboardStats } from "@/features/leads/dashboard-stats"
import { RoadmapNotice } from "@/features/dashboard/roadmap-notice"
import { AppHeader } from "@/components/app-header"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import type { SubscriptionUsage } from "@/lib/types"

export default function DashboardPage() {
  const router = useRouter()
  const t = useTranslations("dashboard")
  const tProjects = useTranslations("projects")
  const [user, setUser] = useState<{ name?: string } | null>(null)
  const [subscription, setSubscription] = useState<SubscriptionUsage | null>(null)
  const [loading, setLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const userResult = await authApi.getCurrentUser()
      if (!userResult.success) {
        router.push("/login")
        return
      }
      setUser(userResult.user)

      const subscriptionResult = await billingApi.getSubscription()
      if (subscriptionResult.success && subscriptionResult.subscription) {
        setSubscription(subscriptionResult.subscription)
      }
    } catch (error) {
      console.error("[MapLeads] Load data error:", error)
      router.push("/login")
    } finally {
      setLoading(false)
    }
  }

  const handleCreateProject = async (name: string) => {
    const result = await projectsApi.create(name)
    if (!result.success) {
      throw new Error(result.message || tProjects("errors.create"))
    }
    setRefreshKey((key) => key + 1)
  }

  const scrollToProjects = () => {
    document.getElementById("projects")?.scrollIntoView({ behavior: "smooth" })
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <AppHeader userName={user?.name} />

      <main className="container mx-auto space-y-8 px-4 py-8">
        {subscription && <TrialBanner subscription={subscription} />}

        <DashboardStats />

        <div className="grid gap-4 md:grid-cols-3">
          <div className="md:col-span-2">
            {subscription ? (
              <UsageCard subscription={subscription} />
            ) : (
              <Card className="h-full">
                <CardHeader>
                  <CardTitle className="text-base">{t("usage.title")}</CardTitle>
                  <CardDescription>{t("usage.unavailable")}</CardDescription>
                </CardHeader>
              </Card>
            )}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("quickActions.title")}</CardTitle>
              <CardDescription>{t("quickActions.description")}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <Button onClick={() => setCreateOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                {t("quickActions.newProject")}
              </Button>
              <Button variant="outline" onClick={scrollToProjects}>
                <Search className="mr-2 h-4 w-4" />
                {t("quickActions.newSearch")}
              </Button>
            </CardContent>
          </Card>
        </div>

        <RoadmapNotice />

        <section id="projects">
          <ProjectsList refreshKey={refreshKey} />
        </section>
      </main>

      <ProjectDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        mode="create"
        onSubmit={handleCreateProject}
      />
    </div>
  )
}
