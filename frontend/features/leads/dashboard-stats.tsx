"use client"

import { useEffect, useState } from "react"
import { Sparkles, Users, PhoneCall, ThumbsUp } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { leadsApi } from "@/features/leads/api"
import type { LeadStats } from "@/lib/types"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

// The four funnel tiles rendered on the dashboard, in order. `discarded` is
// intentionally not shown (see issue #55).
const TILES: { key: keyof LeadStats; label: string; icon: LucideIcon }[] = [
  { key: "total", label: "Total leads", icon: Users },
  { key: "new", label: "New", icon: Sparkles },
  { key: "contacted", label: "Contacted", icon: PhoneCall },
  { key: "interested", label: "Interested", icon: ThumbsUp },
]

/**
 * A row of data-backed stat tiles giving a lead-funnel snapshot. Fetches
 * account-wide counts on mount. While loading it shows skeleton tiles; on
 * failure it hides itself so the rest of the dashboard is unaffected.
 */
export function DashboardStats() {
  const [stats, setStats] = useState<LeadStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    leadsApi
      .stats()
      .then((result) => {
        if (active && result.success && result.stats) {
          setStats(result.stats)
        }
      })
      .catch((error) => {
        console.error("[MapLeads] Load lead stats error:", error)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  if (loading) {
    return (
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        {TILES.map((tile) => (
          <Card key={tile.key}>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {tile.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  // Fetch failed — degrade gracefully by rendering nothing.
  if (!stats) {
    return null
  }

  return (
    <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
      {TILES.map((tile) => {
        const Icon = tile.icon
        return (
          <Card key={tile.key}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Icon className="h-4 w-4 text-primary" />
                {tile.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {stats[tile.key].toLocaleString()}
              </p>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
