"use client"

import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
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
      setError("Project name is required.")
      return
    }

    setSubmitting(true)
    setError(null)
    try {
      await onSubmit(trimmed)
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.")
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
            <DialogTitle>{isCreate ? "New project" : "Rename project"}</DialogTitle>
            <DialogDescription>
              {isCreate
                ? "Create a project to group its searches and leads."
                : "Give this project a new name."}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-2 py-4">
            <Label htmlFor="project-name">Project name</Label>
            <Input
              id="project-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. Dental clinics — Madrid"
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
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isCreate ? "Create" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
