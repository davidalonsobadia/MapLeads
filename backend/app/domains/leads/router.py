from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.auth.models import User
from app.domains.auth.utils import get_verified_user

from . import schemas, service

# Leads live under a project for collection routes and are addressed directly by
# id for item routes, so this router declares full paths instead of a single prefix.
router = APIRouter(tags=["leads"])


@router.post(
    "/projects/{project_id}/leads",
    response_model=schemas.LeadSaveResult,
    status_code=status.HTTP_201_CREATED,
)
def save_leads(
    project_id: int,
    data: schemas.LeadSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Save selected search results as leads under a project, deduplicating by place_id."""
    return service.LeadService(db).save_leads(current_user.id, project_id, data.items)


@router.get("/projects/{project_id}/leads", response_model=List[schemas.LeadResponse])
def list_leads(
    project_id: int,
    status: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """List a project's leads, optionally filtered by status and case-insensitive name search."""
    return service.LeadService(db).list_leads(current_user.id, project_id, status, q)


@router.get("/projects/{project_id}/leads/place-ids", response_model=List[str])
def existing_place_ids(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Return the place_ids already saved in a project (used to mark search results)."""
    return service.LeadService(db).existing_place_ids(current_user.id, project_id)


@router.get("/leads/{lead_id}", response_model=schemas.LeadResponse)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Get one of the current user's leads. Returns 404 if not owned/found."""
    return service.LeadService(db).get_lead(current_user.id, lead_id)


@router.patch("/leads/{lead_id}", response_model=schemas.LeadResponse)
def update_lead(
    lead_id: int,
    data: schemas.LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Update a lead's status and/or linkedin_url. Invalid status returns 422."""
    return service.LeadService(db).update_lead(current_user.id, lead_id, data)


@router.post(
    "/leads/{lead_id}/notes",
    response_model=schemas.LeadNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_note(
    lead_id: int,
    data: schemas.LeadNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Add a note or reminder to an owned lead. Reminder without a date returns 422."""
    return service.LeadService(db).add_note(current_user.id, lead_id, data)


@router.get("/leads/{lead_id}/notes", response_model=List[schemas.LeadNoteResponse])
def list_notes(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """List an owned lead's notes and reminders, newest first."""
    return service.LeadService(db).list_notes(current_user.id, lead_id)


@router.delete(
    "/leads/{lead_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_note(
    lead_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Delete a note that lives under an owned lead. Returns 404 if not found there."""
    service.LeadService(db).delete_note(current_user.id, lead_id, note_id)
