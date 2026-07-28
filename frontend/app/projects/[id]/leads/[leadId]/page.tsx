import Link from "next/link"
import { getTranslations } from "next-intl/server"
import { ArrowLeft, MapPin } from "lucide-react"

import { config } from "@/lib/config"
import { Button } from "@/components/ui/button"
import { LeadDetail } from "@/features/leads/lead-detail"

interface LeadDetailPageProps {
  params: Promise<{ id: string; leadId: string }>
}

export default async function LeadDetailPage({ params }: LeadDetailPageProps) {
  const { id, leadId } = await params
  const t = await getTranslations("leads")

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto flex items-center justify-between px-4 py-4">
          <Link href={config.routes.dashboard} className="flex items-center gap-2">
            <MapPin className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">MapLeads</span>
          </Link>
          <Button variant="ghost" size="sm" asChild>
            <Link href={config.routes.project(id)}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t("backToProject")}
            </Link>
          </Button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <LeadDetail leadId={leadId} />
      </main>
    </div>
  )
}
