import Link from "next/link"
import { getTranslations } from "next-intl/server"
import { MapPin } from "lucide-react"

import { config } from "@/lib/config"
import { Button } from "@/components/ui/button"
import { AnonymousSearch } from "@/features/anonymous-search/anonymous-search"

// Public "Try a free search" page (#102). Unauthenticated: it hosts the
// anonymous search experience and mirrors the landing page's header/footer.
export default async function TrySearchPage() {
  const t = await getTranslations("anonymousSearch")
  const tl = await getTranslations("landing")

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto flex items-center justify-between px-4 py-4">
          <Link href={config.routes.home} className="flex items-center gap-2">
            <MapPin className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">MapLeads</span>
          </Link>
          <div className="flex items-center gap-4">
            <Button variant="ghost" asChild>
              <Link href={config.routes.login}>{tl("signIn")}</Link>
            </Button>
            <Button asChild>
              <Link href={config.routes.register}>{tl("getStarted")}</Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto max-w-2xl px-4 py-12">
        <div className="mb-8 text-center">
          <h1 className="mb-3 text-3xl font-bold text-balance">{t("title")}</h1>
          <p className="text-muted-foreground text-pretty">{t("subtitle")}</p>
        </div>

        <AnonymousSearch />
      </main>

      <footer className="mt-20 border-t">
        <div className="container mx-auto px-4 py-8 text-center text-muted-foreground">
          <p>{tl("footer.copyright")}</p>
        </div>
      </footer>
    </div>
  )
}
