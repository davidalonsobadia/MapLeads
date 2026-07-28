from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Allowed location kinds, mirrored by the CheckConstraint on the model.
LOCATION_TYPES = ("text", "point")


class SearchRequest(BaseModel):
    """A keyword+location search to run against the Places client.

    Provide ``location_text`` for a ``text`` search, or ``lat``/``lng``/
    ``radius_km`` for a ``point`` search. Supplying the wrong combination for the
    chosen ``location_type`` fails validation (HTTP 422).
    """

    keyword: str = Field(..., min_length=1)
    location_type: Literal["text", "point"]
    location_text: Optional[str] = None
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    radius_km: Optional[float] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _location_fields_match_type(self) -> "SearchRequest":
        if self.location_type == "text":
            if not (self.location_text and self.location_text.strip()):
                raise ValueError("location_text is required when location_type is 'text'")
        else:  # point
            missing = [
                name
                for name, value in (
                    ("lat", self.lat),
                    ("lng", self.lng),
                    ("radius_km", self.radius_km),
                )
                if value is None
            ]
            if missing:
                raise ValueError(
                    "lat, lng and radius_km are required when location_type is 'point'; "
                    f"missing: {', '.join(missing)}"
                )
        return self


class SearchResultItem(BaseModel):
    """A single normalized place, flagged if already saved as a lead."""

    place_id: str
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    category: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    already_saved: bool = False


class SearchRunResponse(BaseModel):
    """The outcome of running a search: the results plus summary counts."""

    search_id: int
    result_count: int
    already_saved_count: int
    results: List[SearchResultItem]


class AnonymousSearchResultItem(BaseModel):
    """A masked place for the unauthenticated funnel.

    Only non-contact identity fields are exposed: no phone, website or
    coordinates, and no ``already_saved`` flag (there is no user to save for).
    """

    place_id: str
    name: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None


class AnonymousSearchResponse(BaseModel):
    """A capped, contact-masked search result for anonymous visitors.

    ``visitor_token`` is a freshly issued signed token the caller must persist
    and replay in the ``X-Anonymous-Search-Token`` header on the next request;
    its presence marks the single free search as already used.
    """

    result_count: int
    total_available: int
    results: List[AnonymousSearchResultItem]
    visitor_token: str


class SearchHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    keyword: str
    location_type: str
    params: dict[str, Any]
    result_count: int
    created_at: datetime
