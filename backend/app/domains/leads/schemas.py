from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

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
