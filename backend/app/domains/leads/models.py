from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db.base import Base


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        # Deduplicate the same place saved twice into a project.
        UniqueConstraint("project_id", "place_id", name="uq_leads_project_place"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id"), index=True, nullable=False
    )
    # Denormalized owner reference for cheap ownership queries.
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    place_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    category = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    # Allowed set: new | contacted | interested | discarded.
    status = Column(String, default="new", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LeadNote(Base):
    __tablename__ = "lead_notes"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), index=True, nullable=False)
    # Kind of entry: note | reminder.
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    # Set only for reminders.
    reminder_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
