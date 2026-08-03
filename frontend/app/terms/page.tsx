import Link from "next/link"
import type { Metadata } from "next"
import { getTranslations } from "next-intl/server"
import { MapPin } from "lucide-react"
import { LocaleSwitcher } from "@/components/locale-switcher"

export async function generateMetadata(): Promise<Metadata> {
  const s = await getTranslations("legal.terms")
  return { title: s("metaTitle") }
}

export default async function TermsPage() {
  const t = await getTranslations("legal")
  const s = await getTranslations("legal.terms")

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

        <h1 className="mt-6 text-4xl font-bold text-balance">{s("title")}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{s("updated")}</p>
        <p className="mt-6 text-muted-foreground text-pretty">{s("intro")}</p>

        <div className="mt-12 space-y-10">
          <Section title={s("acceptance.title")} body={s("acceptance.body")} />
          <Section title={s("service.title")} body={s("service.body")} />
          <Section title={s("account.title")} body={s("account.body")} />
          <Section title={s("acceptableUse.title")} body={s("acceptableUse.body")} />
          <Section title={s("billing.title")} body={s("billing.body")} />
          <Section title={s("intellectualProperty.title")} body={s("intellectualProperty.body")} />
          <Section title={s("thirdPartyServices.title")} body={s("thirdPartyServices.body")} />
          <Section title={s("disclaimer.title")} body={s("disclaimer.body")} />
          <Section title={s("liability.title")} body={s("liability.body")} />
          <Section title={s("termination.title")} body={s("termination.body")} />
          <Section title={s("governingLaw.title")} body={s("governingLaw.body")} />
          <Section title={s("changes.title")} body={s("changes.body")} />
          <Section title={s("contact.title")} body={s("contact.body")} />
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
