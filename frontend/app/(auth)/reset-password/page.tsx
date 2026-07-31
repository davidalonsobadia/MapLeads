"use client"

import type React from "react"

import { Suspense, useState, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { authApi } from "@/features/auth/api"
import { useTranslations } from "next-intl"

function ResetPasswordContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const t = useTranslations("auth.resetPassword")
  const [token, setToken] = useState<string | null>(null)
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const tokenFromUrl = searchParams.get("token")
    if (!tokenFromUrl) {
      setError(t("noToken"))
    } else {
      setToken(tokenFromUrl)
    }
  }, [searchParams, t])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!token) {
      setError(t("noToken"))
      return
    }

    if (password !== confirmPassword) {
      setError(t("passwordMismatch"))
      return
    }

    if (password.length < 6) {
      setError(t("passwordTooShort"))
      return
    }

    setLoading(true)

    try {
      const result = await authApi.resetPassword(token, password)

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

  if (!token && !error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl text-center">{t("loading.title")}</CardTitle>
            <CardDescription className="text-center">{t("loading.description")}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  if (error && !token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl text-center">{t("invalidLink.title")}</CardTitle>
            <CardDescription className="text-center text-destructive">{error}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p className="text-sm text-center text-muted-foreground">{t("invalidLink.hint")}</p>
            <Button asChild className="w-full">
              <Link href="/forgot-password">{t("invalidLink.requestNew")}</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">{t("title")}</CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
                {error}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="password">{t("passwordLabel")}</Label>
              <Input
                id="password"
                type="password"
                placeholder={t("passwordPlaceholder")}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">{t("confirmPasswordLabel")}</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder={t("confirmPasswordPlaceholder")}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-4 pt-6">
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? t("submitting") : t("submit")}
            </Button>
            <p className="text-sm text-center text-muted-foreground">
              <Link href="/login" className="text-primary hover:underline">
                {t("backToLogin")}
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}

function ResetPasswordFallback() {
  const t = useTranslations("auth.resetPassword")

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl text-center">{t("loading.title")}</CardTitle>
          <CardDescription className="text-center">{t("loading.description")}</CardDescription>
        </CardHeader>
      </Card>
    </div>
  )
}

// useSearchParams() must be read inside a Suspense boundary so the page can be
// statically prerendered (Next.js App Router requirement).
export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<ResetPasswordFallback />}>
      <ResetPasswordContent />
    </Suspense>
  )
}
