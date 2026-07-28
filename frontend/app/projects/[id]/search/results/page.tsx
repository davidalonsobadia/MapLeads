"use client"

import { Suspense, use } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useTranslations } from "next-intl"
import { ArrowLeft, Loader2, MapPin } from "lucide-react"

import { config } from "@/lib/config"
import { Button } from "@/components/ui/button"
import { SearchResults } from "@/features/search/search-results"

interface SearchResultsPageProps {
  params: Promise<{ id: string }>
}

function SearchResultsContent({ projectId }: { projectId: string }) {
  const searchParams = useSearchParams()
  const searchId = searchParams.get("search_id") ?? ""

  return <SearchResults projectId={projectId} searchId={searchId} />
}

export default function SearchResultsPage({ params }: SearchResultsPageProps) {
  const { id } = use(params)
  const t = useTranslations("search.results")

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto flex items-center justify-between px-4 py-4">
          <Link href={config.routes.dashboard} className="flex items-center gap-2">
            <MapPin className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">MapLeads</span>
          </Link>
          <Button variant="ghost" size="sm" asChild>
            <Link href={config.routes.newSearch(id)}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t("headerNewSearch")}
            </Link>
          </Button>
        </div>
      </header>

      <main className="container mx-auto max-w-6xl px-4 py-8">
        <Suspense
          fallback={
            <div className="flex items-center justify-center py-24">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          }
        >
          <SearchResultsContent projectId={id} />
        </Suspense>
      </main>
    </div>
  )
}
