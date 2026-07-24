"""Tests for the lead notes/reminders service and router.

The ``client`` fixture is authenticated as ``test_user`` (see ``conftest.py``).
Ownership tests seed a second user with their own project and lead directly on
the session and assert that ``test_user`` cannot reach that lead's notes.
"""

from app.domains.auth.models import User
from app.domains.leads.models import Lead, LeadNote
from app.domains.projects.models import Project

PROJECTS = "/api/v1/projects"


def _create_lead(client) -> int:
    project_id = client.post(PROJECTS, json={"name": "Prospects"}).json()["id"]
    return (
        client.post(
            f"{PROJECTS}/{project_id}/leads",
            json={"items": [{"place_id": "p1", "name": "Acme"}]},
        )
        .json()["saved"][0]["id"]
    )


def test_add_note_and_reminder_then_list_newest_first(client):
    """A note and a reminder can be added, then listed newest first."""
    lead_id = _create_lead(client)
    base = f"/api/v1/leads/{lead_id}/notes"

    note = client.post(base, json={"type": "note", "content": "Called them"})
    assert note.status_code == 201
    assert note.json()["type"] == "note"
    assert note.json()["reminder_date"] is None

    reminder = client.post(
        base,
        json={
            "type": "reminder",
            "content": "Follow up",
            "reminder_date": "2026-08-01T10:00:00",
        },
    )
    assert reminder.status_code == 201
    assert reminder.json()["reminder_date"] == "2026-08-01T10:00:00"

    listed = client.get(base)
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 2
    # newest first: the reminder was created after the note
    assert [item["content"] for item in body] == ["Follow up", "Called them"]


def test_reminder_without_date_is_422(client):
    """type=reminder without reminder_date is rejected with 422."""
    lead_id = _create_lead(client)
    base = f"/api/v1/leads/{lead_id}/notes"

    response = client.post(base, json={"type": "reminder", "content": "No date"})
    assert response.status_code == 422
    assert client.get(base).json() == []


def test_invalid_type_is_422(client):
    """A type outside note|reminder is rejected with 422."""
    lead_id = _create_lead(client)
    base = f"/api/v1/leads/{lead_id}/notes"

    response = client.post(base, json={"type": "bogus", "content": "x"})
    assert response.status_code == 422


def test_delete_note(client):
    """A note can be deleted (204) and disappears from the list."""
    lead_id = _create_lead(client)
    base = f"/api/v1/leads/{lead_id}/notes"

    note_id = client.post(base, json={"type": "note", "content": "Temp"}).json()["id"]
    assert client.delete(f"{base}/{note_id}").status_code == 204
    assert client.get(base).json() == []


def test_notes_ownership_is_enforced(client, db_session):
    """Another user's lead notes are invisible and return 404."""
    other_user = User(
        name="Other User",
        email="other@example.com",
        hashed_password="not-a-real-hash",
        is_verified=True,
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    other_project = Project(user_id=other_user.id, name="Other's Project")
    db_session.add(other_project)
    db_session.commit()
    db_session.refresh(other_project)

    other_lead = Lead(
        project_id=other_project.id,
        user_id=other_user.id,
        place_id="secret",
        name="Confidential",
    )
    db_session.add(other_lead)
    db_session.commit()
    db_session.refresh(other_lead)

    other_note = LeadNote(lead_id=other_lead.id, type="note", content="Private")
    db_session.add(other_note)
    db_session.commit()
    db_session.refresh(other_note)

    base = f"/api/v1/leads/{other_lead.id}/notes"

    # notes routes on a lead the caller does not own -> 404
    assert client.get(base).status_code == 404
    assert client.post(base, json={"type": "note", "content": "x"}).status_code == 404
    assert client.delete(f"{base}/{other_note.id}").status_code == 404

    # the other user's note is untouched
    db_session.refresh(other_note)
    assert other_note.content == "Private"
