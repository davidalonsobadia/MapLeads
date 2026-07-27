import csv
import io
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Query, Session
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from app.domains.billing.service import SubscriptionService
from app.domains.projects.models import Project

from . import models, schemas

# Column header -> Lead attribute, in export order.
EXPORT_COLUMNS: Tuple[Tuple[str, str], ...] = (
    ("name", "name"),
    ("address", "address"),
    ("phone", "phone"),
    ("website", "website"),
    ("category", "category"),
    ("status", "status"),
    ("date saved", "created_at"),
)

EXPORT_FORMATS = ("csv", "xlsx")

CSV_MEDIA_TYPE = "text/csv"
XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


class LeadService:
    def __init__(self, db: Session):
        self.db = db

    def _get_owned_project(self, user_id: int, project_id: int) -> Project:
        """Return the project if owned by the user, else raise 404."""
        project = (
            self.db.query(Project)
            .filter(Project.id == project_id, Project.user_id == user_id)
            .first()
        )
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    def save_leads(
        self, user_id: int, project_id: int, items: List[schemas.LeadSaveItem]
    ) -> schemas.LeadSaveResult:
        """Save selected search results as leads under a project.

        Deduplicates by (project_id, place_id): place_ids already saved — or
        repeated within this batch — are skipped and reported, never duplicated
        and never raising an IntegrityError.

        Only the new (non-duplicate) leads count toward the billing quota. The
        quota is checked before inserting anything: when the account is
        read-only (quota exhausted or trial expired) the whole save is rejected
        with 403 and nothing is written. A batch of only duplicates consumes no
        quota and is therefore never blocked.
        """
        self._get_owned_project(user_id, project_id)

        existing = set(self.existing_place_ids(user_id, project_id))
        to_save: List[schemas.LeadSaveItem] = []
        skipped_place_ids: List[str] = []
        seen: set[str] = set()

        for item in items:
            if item.place_id in existing or item.place_id in seen:
                skipped_place_ids.append(item.place_id)
                continue
            seen.add(item.place_id)
            to_save.append(item)

        billing = SubscriptionService(self.db)
        allowed, reason = billing.can_save_leads(user_id, len(to_save))
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)

        saved: List[models.Lead] = []
        for item in to_save:
            lead = models.Lead(
                project_id=project_id,
                user_id=user_id,
                place_id=item.place_id,
                name=item.name,
                address=item.address,
                phone=item.phone,
                website=item.website,
                category=item.category,
            )
            self.db.add(lead)
            saved.append(lead)

        self.db.commit()
        for lead in saved:
            self.db.refresh(lead)

        billing.record_leads_saved(user_id, len(saved))

        return schemas.LeadSaveResult(
            saved=[schemas.LeadResponse.model_validate(lead) for lead in saved],
            skipped_place_ids=skipped_place_ids,
        )

    def _filtered_leads_query(
        self,
        user_id: int,
        project_id: int,
        status: Optional[str] = None,
        q: Optional[str] = None,
    ) -> "Query[models.Lead]":
        """Build the ownership-scoped, filtered, ordered leads query.

        Shared by ``list_leads`` and ``export`` so both honor the exact same
        status/name filters. Assumes ownership has already been verified.
        """
        query = self.db.query(models.Lead).filter(
            models.Lead.project_id == project_id,
            models.Lead.user_id == user_id,
        )
        if status is not None:
            query = query.filter(models.Lead.status == status)
        if q:
            query = query.filter(models.Lead.name.ilike(f"%{q}%"))
        return query.order_by(models.Lead.created_at.desc())

    def list_leads(
        self,
        user_id: int,
        project_id: int,
        status: Optional[str] = None,
        q: Optional[str] = None,
    ) -> List[models.Lead]:
        """List the leads of an owned project, filtered by status and/or name search."""
        self._get_owned_project(user_id, project_id)
        return self._filtered_leads_query(user_id, project_id, status, q).all()

    def export(
        self,
        user_id: int,
        project_id: int,
        status: Optional[str] = None,
        q: Optional[str] = None,
        format: str = "csv",
    ) -> Tuple[bytes, str, str]:
        """Export an owned project's filtered leads as CSV or XLSX.

        Reuses the same filter logic as ``list_leads`` so the export matches
        the currently applied ``status``/``q`` filters. Returns the file
        content, its media type, and a suggested download filename that
        reflects the filtered set.
        """
        if format not in EXPORT_FORMATS:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid format; allowed: {', '.join(EXPORT_FORMATS)}",
            )

        self._get_owned_project(user_id, project_id)
        leads = self._filtered_leads_query(user_id, project_id, status, q).all()

        headers = [header for header, _ in EXPORT_COLUMNS]
        rows = [
            [_export_value(getattr(lead, attr)) for _, attr in EXPORT_COLUMNS]
            for lead in leads
        ]

        filename = _export_filename(project_id, status, q, format)
        if format == "xlsx":
            content = _to_xlsx(headers, rows)
            media_type = XLSX_MEDIA_TYPE
        else:
            content = _to_csv(headers, rows)
            media_type = CSV_MEDIA_TYPE
        return content, media_type, filename

    def existing_place_ids(self, user_id: int, project_id: int) -> List[str]:
        """Return the place_ids already saved in an owned project (for dedup marking)."""
        self._get_owned_project(user_id, project_id)
        rows = (
            self.db.query(models.Lead.place_id)
            .filter(
                models.Lead.project_id == project_id,
                models.Lead.user_id == user_id,
            )
            .all()
        )
        return [row[0] for row in rows]

    def get_stats(self, user_id: int) -> schemas.LeadStatsResponse:
        """Return account-wide lead funnel counts for the user.

        Counts span all of the user's projects (regardless of the parent
        project's ``archived`` flag) using a single grouped count query. Any
        status with no rows is filled with ``0``; ``total`` is the sum of the
        four per-status counts.
        """
        rows = (
            self.db.query(models.Lead.status, func.count(models.Lead.id))
            .filter(models.Lead.user_id == user_id)
            .group_by(models.Lead.status)
            .all()
        )
        counts = {status_value: count for status_value, count in rows}
        by_status = {
            status_value: counts.get(status_value, 0)
            for status_value in schemas.ALLOWED_STATUSES
        }
        return schemas.LeadStatsResponse(
            total=sum(by_status.values()),
            **by_status,
        )

    def get_lead(self, user_id: int, lead_id: int) -> models.Lead:
        """Get a single lead owned by the user or raise 404."""
        lead = (
            self.db.query(models.Lead)
            .filter(models.Lead.id == lead_id, models.Lead.user_id == user_id)
            .first()
        )
        if lead is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found",
            )
        return lead

    def update_lead(
        self, user_id: int, lead_id: int, data: schemas.LeadUpdate
    ) -> models.Lead:
        """Partially update a lead's status and/or linkedin_url.

        Rejects a status outside the allowed set with 422.
        """
        lead = self.get_lead(user_id, lead_id)
        updates = data.model_dump(exclude_unset=True)

        if "status" in updates and updates["status"] not in schemas.ALLOWED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status; allowed: {', '.join(schemas.ALLOWED_STATUSES)}",
            )

        for field, value in updates.items():
            setattr(lead, field, value)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def add_note(
        self, user_id: int, lead_id: int, data: schemas.LeadNoteCreate
    ) -> models.LeadNote:
        """Add a note or reminder to an owned lead's timeline.

        Ownership is enforced through the parent lead. ``reminder_date`` is
        required for reminders, but that is validated at the schema layer.
        """
        self.get_lead(user_id, lead_id)
        note = models.LeadNote(
            lead_id=lead_id,
            type=data.type,
            content=data.content,
            reminder_date=data.reminder_date,
        )
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def list_notes(self, user_id: int, lead_id: int) -> List[models.LeadNote]:
        """List an owned lead's notes and reminders, newest first."""
        self.get_lead(user_id, lead_id)
        return (
            self.db.query(models.LeadNote)
            .filter(models.LeadNote.lead_id == lead_id)
            .order_by(
                models.LeadNote.created_at.desc(),
                models.LeadNote.id.desc(),
            )
            .all()
        )

    def delete_note(self, user_id: int, lead_id: int, note_id: int) -> None:
        """Delete a note that lives under an owned lead.

        The note must belong to ``lead_id`` (which must be owned by the user);
        a note under a different lead returns 404 even when the caller owns it.
        """
        self.get_lead(user_id, lead_id)
        note = (
            self.db.query(models.LeadNote)
            .filter(
                models.LeadNote.id == note_id,
                models.LeadNote.lead_id == lead_id,
            )
            .first()
        )
        if note is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found",
            )
        self.db.delete(note)
        self.db.commit()


def _export_value(value: object) -> str:
    """Render a lead attribute as a string cell for export."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        # ISO 8601, seconds precision, no microseconds noise.
        return value.replace(microsecond=0).isoformat()
    return str(value)


def _export_filename(
    project_id: int, status: Optional[str], q: Optional[str], format: str
) -> str:
    """Build a download filename that reflects the filtered set."""
    parts = [f"leads-project-{project_id}"]
    if status:
        parts.append(f"status-{_slugify(status)}")
    if q:
        parts.append(f"q-{_slugify(q)}")
    return f"{'-'.join(parts)}.{format}"


def _slugify(value: str) -> str:
    """Reduce a filter value to a filename-safe token."""
    slug = "".join(c if c.isalnum() else "-" for c in value.lower()).strip("-")
    return slug or "all"


def _to_csv(headers: List[str], rows: List[List[str]]) -> bytes:
    """Serialize headers + rows to UTF-8 CSV bytes (with BOM for Excel)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def _to_xlsx(headers: List[str], rows: List[List[str]]) -> bytes:
    """Serialize headers + rows to an in-memory XLSX workbook."""
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Leads"
    sheet.append(headers)
    for row in rows:
        sheet.append(row)

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
