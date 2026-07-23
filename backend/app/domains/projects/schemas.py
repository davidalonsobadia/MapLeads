from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    archived: Optional[bool] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    archived: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
