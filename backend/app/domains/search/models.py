from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)

from app.db.base import Base


class Search(Base):
    """A recorded keyword+location search run against the Places client.

    Running a search does not save leads; this row is history for the project,
    capturing what was searched and how many results came back.
    """

    __tablename__ = "searches"
    __table_args__ = (
        # Enforce the allowed location kinds at the database layer.
        CheckConstraint(
            "location_type IN ('text', 'point')",
            name="ck_searches_location_type",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    # Cascade so deleting a project removes its search history (ProjectService.delete
    # issues a bare db.delete(project)).
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Denormalized owner reference for ownership queries.
    user_id = Column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    keyword = Column(String, nullable=False)
    # Allowed set: text | point.
    location_type = Column(String, nullable=False)
    # location_text for text searches, or lat/lng/radius_km for point searches.
    params = Column(JSON, nullable=False)
    result_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
