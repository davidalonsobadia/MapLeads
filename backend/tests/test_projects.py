"""Tests for the projects domain CRUD endpoints.

The ``client`` fixture is authenticated as ``test_user`` (see ``conftest.py``).
Ownership tests seed a second user directly on the session and assert that
``test_user`` cannot see or touch that user's projects.
"""

from app.domains.auth.models import User
from app.domains.projects.models import Project

BASE = "/api/v1/projects"


def test_project_crud_happy_path(client):
    """create -> list -> get -> rename -> archive -> delete."""
    # create
    response = client.post(BASE, json={"name": "Acme Corp"})
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Acme Corp"
    assert created["archived"] is False
    project_id = created["id"]

    # list (default excludes archived)
    response = client.get(BASE)
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) == 1
    assert projects[0]["id"] == project_id

    # get
    response = client.get(f"{BASE}/{project_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Acme Corp"

    # rename
    response = client.patch(f"{BASE}/{project_id}", json={"name": "Acme Inc"})
    assert response.status_code == 200
    assert response.json()["name"] == "Acme Inc"
    assert response.json()["archived"] is False

    # archive
    response = client.patch(f"{BASE}/{project_id}", json={"archived": True})
    assert response.status_code == 200
    assert response.json()["archived"] is True
    # name unchanged by the archive-only patch
    assert response.json()["name"] == "Acme Inc"

    # archived project is hidden by default, visible with include_archived
    assert client.get(BASE).json() == []
    assert len(client.get(f"{BASE}?include_archived=true").json()) == 1

    # delete
    response = client.delete(f"{BASE}/{project_id}")
    assert response.status_code == 204
    assert client.get(f"{BASE}/{project_id}").status_code == 404


def test_partial_update_is_independent(client):
    """PATCH supports renaming and archiving independently."""
    project_id = client.post(BASE, json={"name": "First"}).json()["id"]

    # archive without touching the name
    response = client.patch(f"{BASE}/{project_id}", json={"archived": True})
    assert response.json()["name"] == "First"
    assert response.json()["archived"] is True

    # rename without touching archived
    response = client.patch(f"{BASE}/{project_id}", json={"name": "Renamed"})
    assert response.json()["name"] == "Renamed"
    assert response.json()["archived"] is True


def test_ownership_is_enforced(client, db_session):
    """A project owned by another user is invisible and returns 404."""
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

    # invisible in the current user's list
    assert client.get(BASE).json() == []

    # get / patch / delete all 404 for a project the caller does not own
    assert client.get(f"{BASE}/{other_project.id}").status_code == 404
    assert client.patch(f"{BASE}/{other_project.id}", json={"name": "Hijacked"}).status_code == 404
    assert client.delete(f"{BASE}/{other_project.id}").status_code == 404

    # the other user's project is untouched
    db_session.refresh(other_project)
    assert other_project.name == "Other's Project"


def test_empty_name_is_rejected(client):
    """An empty name fails validation with 422."""
    assert client.post(BASE, json={"name": ""}).status_code == 422
    assert client.post(BASE, json={}).status_code == 422

    project_id = client.post(BASE, json={"name": "Valid"}).json()["id"]
    assert client.patch(f"{BASE}/{project_id}", json={"name": ""}).status_code == 422
