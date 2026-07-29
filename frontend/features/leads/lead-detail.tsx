"use client"

// Lead detail screen (PRD sec. 4.6, issue #22).
//
// Shows a saved lead's read-only Google data (name, address, phone, website,
// category), an editable LinkedIn URL and status (persisted via
// `PATCH /leads/{id}`), and a notes/reminders timeline (newest first) backed by
// `GET/POST /leads/{id}/notes`. Reminders render their date with an
// overdue/upcoming visual warning computed with `date-fns`.

import { useCallback, useEffect, useMemo, useState } from "react"
import { useTranslations } from "next-intl"
import {
  differenceInCalendarDays,
  format,
  formatDistanceToNow,
  parseISO,
} from "date-fns"
import {
  AlertTriangle,
  Bell,
  ExternalLink,
  Link2,
  Loader2,
  MapPin,
  MessageSquarePlus,
  Phone,
  Tag,
} from "lucide-react"

import type { Lead, LeadNote } from "@/lib/types"
import {
  getLeadStatusStyle,
  LEAD_STATUS_STYLES,
  LEAD_STATUSES,
  type LeadStatus,
} from "@/lib/lead-status"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { leadsApi } from "./api"

interface LeadDetailProps {
  leadId: string
}

// Only treat http(s) URLs as linkable; anything else is rendered as plain text.
function safeHref(url?: string) {
  return url && /^https?:\/\//i.test(url) ? url : undefined
}

function StatusBadge({ status }: { status: string }) {
  const t = useTranslations("leads.status")
  const style = getLeadStatusStyle(status)
  return (
    <Badge variant="secondary" className={cn("gap-1.5", style.badgeClass)}>
      <span
        className={cn("h-1.5 w-1.5 rounded-full", style.dotClass)}
        aria-hidden="true"
      />
      {t(status in LEAD_STATUS_STYLES ? status : "new")}
    </Badge>
  )
}

type ReminderState = "overdue" | "upcoming" | "future"

// A reminder is "overdue" once its day has passed, "upcoming" within the next
// week (including today), and otherwise "future".
function reminderState(date: Date): ReminderState {
  const days = differenceInCalendarDays(date, new Date())
  if (days < 0) return "overdue"
  if (days <= 7) return "upcoming"
  return "future"
}

// Read-only row of Google data.
function DataRow({
  icon,
  label,
  children,
}: {
  icon?: React.ReactNode
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {icon}
        {label}
      </span>
      <span className="text-sm">{children}</span>
    </div>
  )
}

function ReminderWarning({ date }: { date: Date }) {
  const t = useTranslations("leads.notes")
  const state = reminderState(date)
  if (state === "future") return null

  const relative = formatDistanceToNow(date, { addSuffix: true })
  const overdue = state === "overdue"
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        overdue
          ? "bg-destructive/15 text-destructive"
          : "bg-warning/15 text-warning-foreground",
      )}
    >
      <AlertTriangle className="h-3 w-3" aria-hidden="true" />
      {overdue ? t("overdue", { relative }) : t("due", { relative })}
    </span>
  )
}

function TimelineEntry({ note }: { note: LeadNote }) {
  const t = useTranslations("leads.notes")
  const isReminder = note.type === "reminder"
  const reminderDate = note.reminderDate ? parseISO(note.reminderDate) : null

  return (
    <li className="relative pl-6">
      <span
        className={cn(
          "absolute left-0 top-1.5 flex h-4 w-4 items-center justify-center rounded-full",
          isReminder ? "bg-warning/20 text-warning-foreground" : "bg-accent text-primary",
        )}
        aria-hidden="true"
      >
        {isReminder ? <Bell className="h-2.5 w-2.5" /> : <MessageSquarePlus className="h-2.5 w-2.5" />}
      </span>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium">
          {isReminder ? t("type.reminder") : t("type.note")}
        </span>
        {isReminder && reminderDate && (
          <>
            <span className="text-xs text-muted-foreground">
              {format(reminderDate, "PP")}
            </span>
            <ReminderWarning date={reminderDate} />
          </>
        )}
        <span className="ml-auto text-xs text-muted-foreground">
          {format(parseISO(note.createdAt), "PP p")}
        </span>
      </div>
      <p className="mt-1 whitespace-pre-wrap text-sm">{note.content}</p>
    </li>
  )
}

export function LeadDetail({ leadId }: LeadDetailProps) {
  const t = useTranslations("leads")
  const [lead, setLead] = useState<Lead | null>(null)
  const [notes, setNotes] = useState<LeadNote[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Editable fields.
  const [linkedin, setLinkedin] = useState("")
  const [savingLinkedin, setSavingLinkedin] = useState(false)
  const [savingStatus, setSavingStatus] = useState(false)
  const [fieldError, setFieldError] = useState<string | null>(null)

  // Note composer.
  const [noteType, setNoteType] = useState<"note" | "reminder">("note")
  const [noteContent, setNoteContent] = useState("")
  const [reminderDate, setReminderDate] = useState("")
  const [addingNote, setAddingNote] = useState(false)
  const [noteError, setNoteError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [leadResult, notesResult] = await Promise.all([
        leadsApi.get(leadId),
        leadsApi.listNotes(leadId),
      ])
      if (!leadResult.success || !leadResult.lead) {
        setError(leadResult.message || t("loadFailed"))
        return
      }
      setLead(leadResult.lead)
      setLinkedin(leadResult.lead.linkedinUrl ?? "")
      if (notesResult.success) setNotes(notesResult.notes ?? [])
    } catch {
      setError(t("loadFailed"))
    } finally {
      setLoading(false)
    }
  }, [leadId, t])

  useEffect(() => {
    load()
  }, [load])

  const handleStatusChange = useCallback(
    async (status: string) => {
      if (!lead || status === lead.status) return
      setSavingStatus(true)
      setFieldError(null)
      try {
        const result = await leadsApi.update(leadId, { status })
        if (!result.success || !result.lead) {
          setFieldError(result.message || t("errors.updateStatus"))
          return
        }
        setLead(result.lead)
      } catch {
        setFieldError(t("errors.network"))
      } finally {
        setSavingStatus(false)
      }
    },
    [lead, leadId, t],
  )

  const handleSaveLinkedin = useCallback(async () => {
    if (!lead) return
    const trimmed = linkedin.trim()
    setSavingLinkedin(true)
    setFieldError(null)
    try {
      const result = await leadsApi.update(leadId, { linkedinUrl: trimmed })
      if (!result.success || !result.lead) {
        setFieldError(result.message || t("errors.saveLinkedin"))
        return
      }
      setLead(result.lead)
      setLinkedin(result.lead.linkedinUrl ?? "")
    } catch {
      setFieldError(t("errors.network"))
    } finally {
      setSavingLinkedin(false)
    }
  }, [lead, leadId, linkedin, t])

  const handleAddNote = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault()
      const content = noteContent.trim()
      if (!content) {
        setNoteError(t("errors.emptyNote"))
        return
      }
      if (noteType === "reminder" && !reminderDate) {
        setNoteError(t("errors.missingReminderDate"))
        return
      }
      setAddingNote(true)
      setNoteError(null)
      try {
        // Send the bare `YYYY-MM-DD` string the date input produced. Converting
        // through `new Date(...).toISOString()` would reinterpret local midnight
        // as UTC and shift the day by one east of UTC; the backend parses the
        // date-only value correctly on its own.
        const result = await leadsApi.addNote(leadId, {
          type: noteType,
          content,
          reminderDate: noteType === "reminder" ? reminderDate : null,
        })
        if (!result.success || !result.note) {
          setNoteError(result.message || t("errors.addNote"))
          return
        }
        // Backend returns notes newest-first; prepend the new one to match.
        setNotes((prev) => [result.note as LeadNote, ...prev])
        setNoteContent("")
        setReminderDate("")
        setNoteType("note")
      } catch {
        setNoteError(t("errors.network"))
      } finally {
        setAddingNote(false)
      }
    },
    [leadId, noteType, noteContent, reminderDate, t],
  )

  const linkedinDirty = useMemo(
    () => linkedin.trim() !== (lead?.linkedinUrl ?? ""),
    [linkedin, lead],
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error || !lead) {
    return (
      <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
        {error || t("notFound")}
      </div>
    )
  }

  const websiteHref = safeHref(lead.website)
  const linkedinHref = safeHref(lead.linkedinUrl)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold">{lead.name}</h1>
        <StatusBadge status={lead.status} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Google data + editable fields */}
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {t("businessDetails.title")}
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <DataRow label={t("businessDetails.name")}>{lead.name}</DataRow>
              <DataRow
                icon={<Tag className="h-3 w-3" />}
                label={t("businessDetails.category")}
              >
                {lead.category ?? "—"}
              </DataRow>
              <DataRow
                label={t("businessDetails.address")}
                icon={<MapPin className="h-3 w-3" />}
              >
                {lead.address ?? "—"}
              </DataRow>
              <DataRow
                icon={<Phone className="h-3 w-3" />}
                label={t("businessDetails.phone")}
              >
                {lead.phone ?? "—"}
              </DataRow>
              <DataRow
                icon={<ExternalLink className="h-3 w-3" />}
                label={t("businessDetails.website")}
              >
                {lead.website ? (
                  websiteHref ? (
                    <a
                      href={websiteHref}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      {lead.website}
                    </a>
                  ) : (
                    lead.website
                  )
                ) : (
                  "—"
                )}
              </DataRow>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("tracking.title")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label htmlFor="lead-status">{t("tracking.statusLabel")}</Label>
                <div className="flex items-center gap-2">
                  <Select
                    value={lead.status}
                    onValueChange={handleStatusChange}
                    disabled={savingStatus}
                  >
                    <SelectTrigger id="lead-status" className="w-[200px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {LEAD_STATUSES.map((status: LeadStatus) => (
                        <SelectItem key={status} value={status}>
                          {t(`status.${status}`)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {savingStatus && (
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  )}
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="lead-linkedin">{t("tracking.linkedinLabel")}</Label>
                <div className="flex flex-wrap items-center gap-2">
                  <div className="relative flex-1">
                    <Link2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="lead-linkedin"
                      type="url"
                      inputMode="url"
                      placeholder={t("tracking.linkedinPlaceholder")}
                      value={linkedin}
                      onChange={(event) => setLinkedin(event.target.value)}
                      className="pl-9"
                    />
                  </div>
                  <Button
                    type="button"
                    onClick={handleSaveLinkedin}
                    disabled={!linkedinDirty || savingLinkedin}
                  >
                    {savingLinkedin && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    {t("tracking.save")}
                  </Button>
                </div>
                {linkedinHref && (
                  <a
                    href={linkedinHref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex w-fit items-center gap-1 text-xs text-primary hover:underline"
                  >
                    {t("tracking.openProfile")}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>

              {fieldError && (
                <p className="text-sm text-destructive">{fieldError}</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Notes & reminders timeline */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">{t("notes.title")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={handleAddNote} className="space-y-3">
              <ToggleGroup
                type="single"
                variant="outline"
                value={noteType}
                onValueChange={(value) => {
                  if (value === "note" || value === "reminder") setNoteType(value)
                }}
                className="justify-start"
                aria-label={t("notes.entryTypeAria")}
              >
                <ToggleGroupItem value="note" className="flex-none px-3">
                  {t("notes.type.note")}
                </ToggleGroupItem>
                <ToggleGroupItem value="reminder" className="flex-none px-3">
                  {t("notes.type.reminder")}
                </ToggleGroupItem>
              </ToggleGroup>

              <Textarea
                value={noteContent}
                onChange={(event) => setNoteContent(event.target.value)}
                placeholder={
                  noteType === "reminder"
                    ? t("notes.reminderPlaceholder")
                    : t("notes.notePlaceholder")
                }
                rows={3}
              />

              {noteType === "reminder" && (
                <div className="grid gap-1.5">
                  <Label htmlFor="reminder-date" className="text-xs">
                    {t("notes.reminderDateLabel")}
                  </Label>
                  <Input
                    id="reminder-date"
                    type="date"
                    value={reminderDate}
                    onChange={(event) => setReminderDate(event.target.value)}
                    className="w-fit"
                  />
                </div>
              )}

              {noteError && (
                <p className="text-sm text-destructive">{noteError}</p>
              )}

              <Button type="submit" disabled={addingNote} className="w-full">
                {addingNote ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <MessageSquarePlus className="mr-2 h-4 w-4" />
                )}
                {noteType === "reminder"
                  ? t("notes.addReminder")
                  : t("notes.addNote")}
              </Button>
            </form>

            <Separator />

            {notes.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                {t("notes.empty")}
              </p>
            ) : (
              <ul className="space-y-4">
                {notes.map((note) => (
                  <TimelineEntry key={note.id} note={note} />
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
