from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
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
        # Deduplicate the same Google place within a project.
        UniqueConstraint("project_id", "place_id", name="uq_leads_project_place"),
        # Enforce the documented allowed status set at the database layer.
        CheckConstraint(
            "status IN ('new', 'contacted', 'interested', 'discarded')",
            name="ck_leads_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    # Cascade so deleting a project removes its leads (ProjectService.delete
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
    place_id = Column(String, index=True, nullable=False)  # Google Place ID
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
    # Cascade so deleting a lead removes its notes and reminders.
    lead_id = Column(
        Integer,
        ForeignKey("leads.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    type = Column(String, nullable=False)  # note | reminder
    content = Column(Text, nullable=False)
    reminder_date = Column(DateTime, nullable=True)  # set for reminders
    created_at = Column(DateTime, default=datetime.utcnow)
