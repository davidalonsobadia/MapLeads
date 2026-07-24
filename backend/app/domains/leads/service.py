from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domains.projects.models import Project

from . import models, schemas


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
        """
        self._get_owned_project(user_id, project_id)

        existing = set(self.existing_place_ids(user_id, project_id))
        saved: List[models.Lead] = []
        skipped_place_ids: List[str] = []
        seen: set[str] = set()

        for item in items:
            if item.place_id in existing or item.place_id in seen:
                skipped_place_ids.append(item.place_id)
                continue
            seen.add(item.place_id)
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

        return schemas.LeadSaveResult(
            saved=[schemas.LeadResponse.model_validate(lead) for lead in saved],
            skipped_place_ids=skipped_place_ids,
        )

    def list_leads(
        self,
        user_id: int,
        project_id: int,
        status: Optional[str] = None,
        q: Optional[str] = None,
    ) -> List[models.Lead]:
        """List the leads of an owned project, filtered by status and/or name search."""
        self._get_owned_project(user_id, project_id)

        query = self.db.query(models.Lead).filter(
            models.Lead.project_id == project_id,
            models.Lead.user_id == user_id,
        )
        if status is not None:
            query = query.filter(models.Lead.status == status)
        if q:
            query = query.filter(models.Lead.name.ilike(f"%{q}%"))
        return query.order_by(models.Lead.created_at.desc()).all()

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
        """Add a note or reminder to a lead owned by the user.

        Ownership is enforced through the parent lead (cross-user -> 404). The
        ``type == "reminder"`` requires-``reminder_date`` rule is enforced by the
        schema (422).
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
        """List a lead's notes and reminders, newest first."""
        self.get_lead(user_id, lead_id)
        return (
            self.db.query(models.LeadNote)
            .filter(models.LeadNote.lead_id == lead_id)
            .order_by(models.LeadNote.created_at.desc(), models.LeadNote.id.desc())
            .all()
        )

    def delete_note(self, user_id: int, note_id: int) -> None:
        """Delete a note owned by the user (through its lead) or raise 404."""
        note = (
            self.db.query(models.LeadNote)
            .join(models.Lead, models.LeadNote.lead_id == models.Lead.id)
            .filter(
                models.LeadNote.id == note_id,
                models.Lead.user_id == user_id,
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
