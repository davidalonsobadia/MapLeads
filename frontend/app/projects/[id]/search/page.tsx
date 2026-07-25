"use client"

import { use } from "react"
import Link from "next/link"
import { ArrowLeft, MapPin } from "lucide-react"

import { config } from "@/lib/config"
import { Button } from "@/components/ui/button"
import { NewSearchForm } from "@/features/search/new-search-form"

interface NewSearchPageProps {
  params: Promise<{ id: string }>
}

export default function NewSearchPage({ params }: NewSearchPageProps) {
  const { id } = use(params)

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
              Back to project
            </Link>
          </Button>
        </div>
      </header>

      <main className="container mx-auto max-w-2xl px-4 py-8">
        <NewSearchForm projectId={id} />
      </main>
    </div>
  )
}
