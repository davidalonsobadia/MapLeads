import Link from "next/link"
import type { Metadata } from "next"
import { getTranslations } from "next-intl/server"
import { MapPin } from "lucide-react"
import { LocaleSwitcher } from "@/components/locale-switcher"

export async function generateMetadata(): Promise<Metadata> {
  const p = await getTranslations("legal.privacy")
  return { title: p("metaTitle") }
}

export default async function PrivacyPage() {
  const t = await getTranslations("legal")
  const p = await getTranslations("legal.privacy")

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <MapPin className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">MapLeads</span>
          </Link>
          <LocaleSwitcher />
        </div>
      </header>

      <main className="container mx-auto max-w-3xl px-4 py-16">
        <Link href="/" className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-4">
          {t("backToHome")}
        </Link>

        <h1 className="mt-6 text-4xl font-bold text-balance">{p("title")}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{p("updated")}</p>
        <p className="mt-6 text-muted-foreground text-pretty">{p("intro")}</p>

        <div className="mt-12 space-y-10">
          <Section title={p("controller.title")} body={p("controller.body")} />

          <section>
            <h2 className="text-2xl font-semibold mb-3">{p("dataCollected.title")}</h2>
            <p className="text-muted-foreground mb-3">{p("dataCollected.intro")}</p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>{p("dataCollected.account")}</li>
              <li>{p("dataCollected.oauth")}</li>
              <li>{p("dataCollected.usage")}</li>
              <li>{p("dataCollected.billing")}</li>
              <li>{p("dataCollected.cookies")}</li>
            </ul>
          </section>

          <Section title={p("useOfData.title")} body={p("useOfData.body")} />
          <Section title={p("legalBasis.title")} body={p("legalBasis.body")} />

          <section>
            <h2 className="text-2xl font-semibold mb-3">{p("sharing.title")}</h2>
            <p className="text-muted-foreground mb-3">{p("sharing.intro")}</p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>{p("sharing.google")}</li>
              <li>{p("sharing.github")}</li>
              <li>{p("sharing.stripe")}</li>
              <li>{p("sharing.resend")}</li>
              <li>{p("sharing.sentry")}</li>
              <li>{p("sharing.maps")}</li>
            </ul>
          </section>

          <Section title={p("retention.title")} body={p("retention.body")} />

          <section>
            <h2 className="text-2xl font-semibold mb-3">{p("rights.title")}</h2>
            <p className="text-muted-foreground mb-3">{p("rights.intro")}</p>
            <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
              <li>{p("rights.access")}</li>
              <li>{p("rights.rectification")}</li>
              <li>{p("rights.erasure")}</li>
              <li>{p("rights.portability")}</li>
              <li>{p("rights.objection")}</li>
              <li>{p("rights.restriction")}</li>
              <li>{p("rights.complaint")}</li>
            </ul>
          </section>

          <Section title={p("international.title")} body={p("international.body")} />
          <Section title={p("security.title")} body={p("security.body")} />
          <Section title={p("children.title")} body={p("children.body")} />
          <Section title={p("changes.title")} body={p("changes.body")} />
          <Section title={p("contact.title")} body={p("contact.body")} />
        </div>
      </main>
    </div>
  )
}

function Section({ title, body }: { title: string; body: string }) {
  return (
    <section>
      <h2 className="text-2xl font-semibold mb-3">{title}</h2>
      <p className="text-muted-foreground text-pretty">{body}</p>
    </section>
  )
}
