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


class LeadStatsResponse(BaseModel):
    """Account-wide lead funnel counts for the current user.

    ``total`` equals the sum of the four per-status counts, and each status
    with no leads reports ``0`` (never omitted).
    """

    total: int
    new: int
    contacted: int
    interested: int
    discarded: int


class LeadNoteCreate(BaseModel):
    """A note or a follow-up reminder on the lead timeline.

    ``reminder_date`` is required when ``type`` is ``reminder``; omitting it
    fails validation (HTTP 422).
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
    type: Literal["note", "reminder"]
    content: str
    reminder_date: Optional[datetime] = None
    created_at: datetime
