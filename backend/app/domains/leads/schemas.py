from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Allowed lead status values, mirrored by the CheckConstraint on the model.
ALLOWED_STATUSES = ("new", "contacted", "interested", "discarded")


class LeadSaveItem(BaseModel):
    """A single search result selected to be saved as a lead."""

    place_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    category: Optional[str] = None


class LeadSaveRequest(BaseModel):
    items: List[LeadSaveItem] = Field(..., min_length=1)


class LeadUpdate(BaseModel):
    status: Optional[str] = None
    linkedin_url: Optional[str] = None


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    place_id: str
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    category: Optional[str] = None
    linkedin_url: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class LeadSaveResult(BaseModel):
    saved: List[LeadResponse]
    skipped_place_ids: List[str]


class LeadNoteCreate(BaseModel):
    """A dated note or follow-up reminder on a lead.

    ``reminder_date`` is required when ``type == "reminder"`` and optional
    (typically unset) for plain notes.
    """

    type: Literal["note", "reminder"]
    content: str = Field(..., min_length=1)
    reminder_date: Optional[datetime] = None

    @model_validator(mode="after")
    def _reminder_requires_date(self) -> "LeadNoteCreate":
        if self.type == "reminder" and self.reminder_date is None:
            raise ValueError("reminder_date is required when type is 'reminder'")
        return self


class LeadNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    type: str
    content: str
    reminder_date: Optional[datetime] = None
    created_at: datetime
