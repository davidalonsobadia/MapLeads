"use client"

import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { useTranslations } from "next-intl"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface ProjectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** "create" shows an empty form; "rename" pre-fills the current name. */
  mode: "create" | "rename"
  /** Current name, used to pre-fill the field in "rename" mode. */
  initialName?: string
  /** Persist the name. Should throw on failure so the dialog can surface it. */
  onSubmit: (name: string) => Promise<void>
}

export function ProjectDialog({
  open,
  onOpenChange,
  mode,
  initialName = "",
  onSubmit,
}: ProjectDialogProps) {
  const t = useTranslations("projects.dialog")
  const [name, setName] = useState(initialName)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reset the form whenever the dialog is (re)opened.
  useEffect(() => {
    if (open) {
      setName(initialName)
      setError(null)
      setSubmitting(false)
    }
  }, [open, initialName])

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      setError(t("nameRequired"))
      return
    }

    setSubmitting(true)
    setError(null)
    try {
      await onSubmit(trimmed)
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : t("genericError"))
    } finally {
      setSubmitting(false)
    }
  }

  const isCreate = mode === "create"

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{isCreate ? t("createTitle") : t("renameTitle")}</DialogTitle>
            <DialogDescription>
              {isCreate ? t("createDescription") : t("renameDescription")}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-2 py-4">
            <Label htmlFor="project-name">{t("nameLabel")}</Label>
            <Input
              id="project-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={t("namePlaceholder")}
              autoFocus
              disabled={submitting}
            />
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={submitting}
            >
              {t("cancel")}
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isCreate ? t("create") : t("save")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
