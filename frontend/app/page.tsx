import Link from "next/link"
import { Button } from "@/components/ui/button"
import { MapPin, Search, Shield, Users } from "lucide-react"

export default function HomePage() {
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
              <Link href="/login">Sign in</Link>
            </Button>
            <Button asChild>
              <Link href="/register">Get started</Link>
            </Button>
          </div>
        </div>
      </header>

      <main>
        <section className="container mx-auto px-4 py-20 text-center">
          <h1 className="text-5xl font-bold mb-6 text-balance">
            Find local business leads with <span className="text-primary">MapLeads</span>
          </h1>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto text-pretty">
            Search Google Maps by keyword and location, save the businesses that matter, and track
            every lead for every client from one mini-CRM built for agencies.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Button size="lg" asChild>
              <Link href="/register">Start for free</Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/login">Sign in</Link>
            </Button>
          </div>
        </section>

        <section className="container mx-auto px-4 py-20">
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6 border rounded-lg bg-card">
              <Search className="h-12 w-12 text-primary mb-4" />
              <h3 className="text-xl font-semibold mb-2">Search by keyword + location</h3>
              <p className="text-muted-foreground">
                Find businesses on Google Maps and choose exactly which results become leads.
              </p>
            </div>
            <div className="p-6 border rounded-lg bg-card">
              <Users className="h-12 w-12 text-primary mb-4" />
              <h3 className="text-xl font-semibold mb-2">Organized by project</h3>
              <p className="text-muted-foreground">
                Group leads by client, track status, add notes and reminders as you follow up.
              </p>
            </div>
            <div className="p-6 border rounded-lg bg-card">
              <Shield className="h-12 w-12 text-primary mb-4" />
              <h3 className="text-xl font-semibold mb-2">Secure & Private</h3>
              <p className="text-muted-foreground">
                Your data is protected with email verification and secure authentication.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t mt-20">
        <div className="container mx-auto px-4 py-8 text-center text-muted-foreground">
          <p>© 2026 MapLeads. Built with Next.js and modern web technologies.</p>
        </div>
      </footer>
    </div>
  )
}
