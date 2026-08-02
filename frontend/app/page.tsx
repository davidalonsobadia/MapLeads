import Link from "next/link"
import { getTranslations } from "next-intl/server"
import { Button } from "@/components/ui/button"
import { MapPin, Search, Shield, Users } from "lucide-react"

export default async function HomePage() {
  const t = await getTranslations("landing")

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">MapLeads</span>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="ghost" asChild>
              <Link href="/login">{t("signIn")}</Link>
            </Button>
            <Button asChild>
              <Link href="/register">{t("getStarted")}</Link>
            </Button>
          </div>
        </div>
      </header>

      <main>
        <section className="container mx-auto px-4 py-20 text-center">
          <h1 className="text-5xl font-bold mb-6 text-balance">
            {t.rich("hero.title", {
              highlight: (chunks) => <span className="text-primary">{chunks}</span>,
            })}
          </h1>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto text-pretty">
            {t("hero.subtitle")}
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Button size="lg" asChild>
              <Link href="/register">{t("hero.startFree")}</Link>
            </Button>
            <Button size="lg" variant="secondary" asChild>
              <Link href="/try">{t("hero.tryFree")}</Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/login">{t("hero.signIn")}</Link>
            </Button>
          </div>
        </section>

        <section className="container mx-auto px-4 py-20">
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6 border rounded-lg bg-card">
              <Search className="h-12 w-12 text-primary mb-4" />
              <h3 className="text-xl font-semibold mb-2">{t("features.search.title")}</h3>
              <p className="text-muted-foreground">{t("features.search.description")}</p>
            </div>
            <div className="p-6 border rounded-lg bg-card">
              <Users className="h-12 w-12 text-primary mb-4" />
              <h3 className="text-xl font-semibold mb-2">{t("features.projects.title")}</h3>
              <p className="text-muted-foreground">{t("features.projects.description")}</p>
            </div>
            <div className="p-6 border rounded-lg bg-card">
              <Shield className="h-12 w-12 text-primary mb-4" />
              <h3 className="text-xl font-semibold mb-2">{t("features.secure.title")}</h3>
              <p className="text-muted-foreground">{t("features.secure.description")}</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t mt-20">
        <div className="container mx-auto px-4 py-8 text-center text-muted-foreground">
          <p>
            {t.rich("footer.copyright", {
              koalvia: (chunks) => (
                <a
                  href="https://www.koalvia.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline underline-offset-4 hover:text-foreground"
                >
                  {chunks}
                </a>
              ),
            })}
          </p>
        </div>
      </footer>
    </div>
  )
}
