"""Tests for the leads domain models.

These exercise the ORM layer directly against the in-memory SQLite database
(the ``db_session`` fixture): a lead can be persisted, the
``(project_id, place_id)`` uniqueness that backs deduplication is enforced,
and a ``LeadNote`` can be attached and read back.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.domains.leads.models import Lead, LeadNote
from app.domains.projects.models import Project


def _make_project(db_session, user) -> Project:
    project = Project(user_id=user.id, name="Acme Corp")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def test_insert_lead(db_session, test_user):
    """A lead persists with its defaults."""
    project = _make_project(db_session, test_user)
    lead = Lead(
        project_id=project.id,
        user_id=test_user.id,
        place_id="ChIJ_place_1",
        name="Coffee Shop",
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)

    assert lead.id is not None
    assert lead.status == "new"
    assert lead.address is None
    assert lead.created_at is not None


def test_duplicate_place_in_project_rejected(db_session, test_user):
    """(project_id, place_id) is unique so the same place cannot be saved twice."""
    project = _make_project(db_session, test_user)
    db_session.add(
        Lead(
            project_id=project.id,
            user_id=test_user.id,
            place_id="ChIJ_dup",
            name="First",
        )
    )
    db_session.commit()

    db_session.add(
        Lead(
            project_id=project.id,
            user_id=test_user.id,
            place_id="ChIJ_dup",
            name="Duplicate",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_same_place_in_different_projects_allowed(db_session, test_user):
    """The unique constraint is scoped per project, not global."""
    project_a = _make_project(db_session, test_user)
    project_b = _make_project(db_session, test_user)
    db_session.add_all(
        [
            Lead(
                project_id=project_a.id,
                user_id=test_user.id,
                place_id="ChIJ_shared",
                name="In A",
            ),
            Lead(
                project_id=project_b.id,
                user_id=test_user.id,
                place_id="ChIJ_shared",
                name="In B",
            ),
        ]
    )
    db_session.commit()

    assert db_session.query(Lead).count() == 2


def test_attach_and_read_lead_note(db_session, test_user):
    """A note (and a reminder) can be attached to a lead and read back."""
    project = _make_project(db_session, test_user)
    lead = Lead(
        project_id=project.id,
        user_id=test_user.id,
        place_id="ChIJ_notes",
        name="Bakery",
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)

    note = LeadNote(lead_id=lead.id, type="note", content="Called, no answer")
    db_session.add(note)
    db_session.commit()

    stored = db_session.query(LeadNote).filter_by(lead_id=lead.id).one()
    assert stored.type == "note"
    assert stored.content == "Called, no answer"
    assert stored.reminder_date is None
    assert stored.created_at is not None
