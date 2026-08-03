"use client"

import { useState } from "react"
import { Loader2 } from "lucide-react"
import { useTranslations } from "next-intl"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

interface DeleteSearchDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  keyword: string
  /** Perform the deletion. Should throw on failure so the dialog can surface it. */
  onConfirm: () => Promise<void>
}

export function DeleteSearchDialog({
  open,
  onOpenChange,
  keyword,
  onConfirm,
}: DeleteSearchDialogProps) {
  const t = useTranslations("search.deleteDialog")
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleConfirm = async (event: React.MouseEvent) => {
    // Keep the dialog open until the request settles.
    event.preventDefault()
    setDeleting(true)
    setError(null)
    try {
      await onConfirm()
      onOpenChange(false)
    } catch (err) {
      console.error("[MapLeads] Delete search failed:", err)
      setError(t("error"))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("title", { keyword })}</AlertDialogTitle>
          <AlertDialogDescription>{t("description")}</AlertDialogDescription>
        </AlertDialogHeader>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleting}>{t("cancel")}</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={deleting}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t("confirm")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
