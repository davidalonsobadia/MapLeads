"""Tests for the leads domain models.

These exercise the ORM models directly against the in-memory SQLite database
(see ``conftest.py``): default status, the (project_id, place_id) uniqueness
constraint, cross-project allowance, and note attachment/read-back.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.domains.auth.models import User
from app.domains.leads.models import Lead, LeadNote
from app.domains.projects.models import Project


def _make_user_and_project(db_session) -> tuple[User, Project]:
    user = User(
        name="Lead Owner",
        email="owner@example.com",
        hashed_password="not-a-real-hash",
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = Project(user_id=user.id, name="Prospects")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return user, project


def test_insert_lead_with_defaults(db_session):
    """A Lead persists and defaults status to ``new``."""
    user, project = _make_user_and_project(db_session)

    lead = Lead(
        project_id=project.id,
        user_id=user.id,
        place_id="ChIJabc123",
        name="Acme Cafe",
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)

    assert lead.id is not None
    assert lead.status == "new"
    assert lead.created_at is not None


def test_duplicate_project_place_is_rejected(db_session):
    """A second lead with the same (project_id, place_id) raises IntegrityError."""
    user, project = _make_user_and_project(db_session)

    db_session.add(
        Lead(
            project_id=project.id,
            user_id=user.id,
            place_id="ChIJdup",
            name="First",
        )
    )
    db_session.commit()

    db_session.add(
        Lead(
            project_id=project.id,
            user_id=user.id,
            place_id="ChIJdup",
            name="Duplicate",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_same_place_allowed_in_different_projects(db_session):
    """The same place_id can be saved once per project."""
    user, project = _make_user_and_project(db_session)
    other_project = Project(user_id=user.id, name="Second List")
    db_session.add(other_project)
    db_session.commit()
    db_session.refresh(other_project)

    db_session.add(
        Lead(project_id=project.id, user_id=user.id, place_id="ChIJshared", name="A")
    )
    db_session.add(
        Lead(
            project_id=other_project.id,
            user_id=user.id,
            place_id="ChIJshared",
            name="B",
        )
    )
    db_session.commit()

    assert db_session.query(Lead).count() == 2


def test_attach_and_read_back_note(db_session):
    """A LeadNote can be attached to a lead and read back."""
    user, project = _make_user_and_project(db_session)
    lead = Lead(
        project_id=project.id,
        user_id=user.id,
        place_id="ChIJnote",
        name="With Notes",
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)

    note = LeadNote(lead_id=lead.id, type="note", content="Called, left voicemail.")
    db_session.add(note)
    db_session.commit()

    stored = db_session.query(LeadNote).filter_by(lead_id=lead.id).one()
    assert stored.type == "note"
    assert stored.content == "Called, left voicemail."
    assert stored.reminder_date is None
    assert stored.created_at is not None
