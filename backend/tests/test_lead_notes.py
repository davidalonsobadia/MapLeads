"""Tests for the lead notes and reminders timeline (service and router).

The ``client`` fixture is authenticated as ``test_user`` (see ``conftest.py``).
Ownership tests seed a second user and their project/lead directly on the
session and assert that ``test_user`` cannot reach that data.
"""

from app.domains.auth.models import User
from app.domains.leads.models import Lead, LeadNote
from app.domains.projects.models import Project

PROJECTS = "/api/v1/projects"


def _create_lead(client, place_id="p1", name="Acme") -> int:
    """Create a project + a single lead and return the lead id."""
    project_id = client.post(PROJECTS, json={"name": "Prospects"}).json()["id"]
    base = f"{PROJECTS}/{project_id}/leads"
    return client.post(
        base, json={"items": [{"place_id": place_id, "name": name}]}
    ).json()["saved"][0]["id"]


def test_create_list_and_delete_notes(client):
    """Notes and reminders are created, listed newest first, and deletable."""
    lead_id = _create_lead(client)
    base = f"/api/v1/leads/{lead_id}/notes"

    first = client.post(base, json={"type": "note", "content": "Called, left a voicemail"})
    assert first.status_code == 201
    assert first.json()["type"] == "note"

    second = client.post(
        base,
        json={
            "type": "reminder",
            "content": "Follow up",
            "reminder_date": "2026-08-01T09:00:00",
        },
    )
    assert second.status_code == 201
    reminder = second.json()
    assert reminder["type"] == "reminder"
    assert reminder["reminder_date"] == "2026-08-01T09:00:00"

    # Newest first: the reminder was created last, so it comes first.
    notes = client.get(base).json()
    assert [n["content"] for n in notes] == ["Follow up", "Called, left a voicemail"]

    # Delete the first-created note; the list then holds only the reminder.
    note_id = notes[1]["id"]
    assert client.delete(f"{base}/{note_id}").status_code == 204
    remaining = client.get(base).json()
    assert [n["id"] for n in remaining] == [reminder["id"]]


def test_reminder_without_date_returns_422(client):
    """A reminder created without a reminder_date fails validation with 422."""
    lead_id = _create_lead(client)
    base = f"/api/v1/leads/{lead_id}/notes"

    response = client.post(base, json={"type": "reminder", "content": "No date"})
    assert response.status_code == 422
    # A plain note still needs no date.
    assert client.post(base, json={"type": "note", "content": "OK"}).status_code == 201


def test_delete_missing_note_returns_404(client):
    """Deleting a note id that does not exist returns 404."""
    lead_id = _create_lead(client)
    assert client.delete(f"/api/v1/leads/{lead_id}/notes/9999").status_code == 404


def test_delete_note_wrong_lead_returns_404(client):
    """A note is scoped to its lead: deleting it under another owned lead 404s."""
    lead_id = _create_lead(client, place_id="p1", name="Lead One")
    other_lead_id = _create_lead(client, place_id="p2", name="Lead Two")

    note_id = client.post(
        f"/api/v1/leads/{lead_id}/notes",
        json={"type": "note", "content": "Belongs to lead one"},
    ).json()["id"]

    # The note belongs to lead_id, not other_lead_id -> 404 and it survives.
    assert (
        client.delete(f"/api/v1/leads/{other_lead_id}/notes/{note_id}").status_code
        == 404
    )
    assert [n["id"] for n in client.get(f"/api/v1/leads/{lead_id}/notes").json()] == [
        note_id
    ]


def test_notes_ownership_is_enforced(client, db_session):
    """Another user's lead notes are invisible: create/list/delete return 404."""
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

    other_note = LeadNote(
        lead_id=other_lead.id, type="note", content="Private note"
    )
    db_session.add(other_note)
    db_session.commit()
    db_session.refresh(other_note)

    base = f"/api/v1/leads/{other_lead.id}/notes"
    assert client.get(base).status_code == 404
    assert client.post(base, json={"type": "note", "content": "x"}).status_code == 404
    assert client.delete(f"{base}/{other_note.id}").status_code == 404

    # The other user's note is untouched.
    db_session.refresh(other_note)
    assert other_note.content == "Private note"
