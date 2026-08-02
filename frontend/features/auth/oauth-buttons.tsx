"use client"

import { Button } from "@/components/ui/button"
import { config } from "@/lib/config"
import { useTranslations } from "next-intl"

function GoogleIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09a6.6 6.6 0 0 1 0-4.18V7.07H2.18a11 11 0 0 0 0 9.86l3.66-2.84Z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38Z"
      />
    </svg>
  )
}

/**
 * Social login entry points shown on the login and register pages.
 * Each button is a top-level browser navigation to the OAuth start route
 * (not a fetch), so a plain anchor is used.
 */
export function OAuthButtons() {
  const t = useTranslations("auth.oauth")

  return (
    <div className="flex w-full flex-col gap-4">
      <div className="relative flex items-center">
        <div className="flex-1 border-t border-border" />
        <span className="px-3 text-xs uppercase text-muted-foreground">{t("divider")}</span>
        <div className="flex-1 border-t border-border" />
      </div>
      <div className="flex flex-col gap-2">
        <Button asChild variant="outline" className="w-full">
          <a href={config.api.endpoints.auth.oauthStart("google")}>
            <GoogleIcon />
            {t("continueWithGoogle")}
          </a>
        </Button>
      </div>
    </div>
  )
}
