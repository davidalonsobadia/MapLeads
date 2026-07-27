"use client"

import type React from "react"

import { Suspense, useState, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { authApi } from "@/features/auth/api"
import { useTranslations } from "next-intl"

function VerifyEmailContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const t = useTranslations("auth.verifyEmail")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const verifyToken = async () => {
      const token = searchParams.get("token")

      if (!token) {
        setError(t("noToken"))
        setLoading(false)
        return
      }

      try {
        const result = await authApi.verifyEmail(token)

        if (result.success) {
          setSuccess(true)
          setTimeout(() => {
            router.push("/login")
          }, 2000)
        } else {
          setError(result.message || t("failed"))
        }
      } catch (err) {
        setError(t("genericError"))
      } finally {
        setLoading(false)
      }
    }

    verifyToken()
  }, [searchParams, router, t])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl text-center">{t("verifying.title")}</CardTitle>
            <CardDescription className="text-center">{t("verifying.description")}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl text-center">{t("success.title")}</CardTitle>
            <CardDescription className="text-center">{t("success.description")}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl text-center">{t("error.title")}</CardTitle>
            <CardDescription className="text-center text-destructive">{error}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p className="text-sm text-center text-muted-foreground">{t("error.hint")}</p>
            <Button asChild className="w-full">
              <Link href="/login">{t("error.backToLogin")}</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return null
}

function VerifyEmailFallback() {
  const t = useTranslations("auth.verifyEmail")

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl text-center">{t("verifying.title")}</CardTitle>
          <CardDescription className="text-center">{t("verifying.description")}</CardDescription>
        </CardHeader>
      </Card>
    </div>
  )
}

// useSearchParams() must be read inside a Suspense boundary so the page can be
// statically prerendered (Next.js App Router requirement).
export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<VerifyEmailFallback />}>
      <VerifyEmailContent />
    </Suspense>
  )
}
