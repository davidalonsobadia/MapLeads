"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { CreditCard, LogOut, Loader2, MapPin, Plus, Search } from "lucide-react"
import { config } from "@/lib/config"
import { authApi } from "@/features/auth/api"
import { billingApi } from "@/features/billing/api"
import { TrialBanner } from "@/features/billing/trial-banner"
import { UsageCard } from "@/features/billing/usage-card"
import { ProjectsList } from "@/features/projects/projects-list"
import { ProjectDialog } from "@/features/projects/project-dialog"
import { projectsApi } from "@/features/projects/api"
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

  const handleLogout = async () => {
    await authApi.logout()
    router.push("/login")
  }

  const handleCreateProject = async (name: string) => {
    const result = await projectsApi.create(name)
    if (!result.success) {
      throw new Error(result.message || "Failed to create the project.")
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
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MapPin className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">MapLeads</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">
                Welcome, <strong>{user?.name}</strong>
              </span>
              <Button variant="ghost" size="sm" asChild>
                <Link href={config.routes.billing}>
                  <CreditCard className="h-4 w-4 mr-2" />
                  Billing
                </Link>
              </Button>
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto space-y-8 px-4 py-8">
        {subscription && <TrialBanner subscription={subscription} />}

        <div className="grid gap-4 md:grid-cols-3">
          <div className="md:col-span-2">
            {subscription ? (
              <UsageCard subscription={subscription} />
            ) : (
              <Card className="h-full">
                <CardHeader>
                  <CardTitle className="text-base">Leads this month</CardTitle>
                  <CardDescription>Usage is unavailable right now.</CardDescription>
                </CardHeader>
              </Card>
            )}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Quick actions</CardTitle>
              <CardDescription>Start something new.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <Button onClick={() => setCreateOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                New project
              </Button>
              <Button variant="outline" onClick={scrollToProjects}>
                <Search className="mr-2 h-4 w-4" />
                New search
              </Button>
            </CardContent>
          </Card>
        </div>

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
