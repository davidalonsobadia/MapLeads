"""Tests for the leads domain service and router.

The ``client`` fixture is authenticated as ``test_user`` (see ``conftest.py``).
Ownership tests seed a second user and their project/lead directly on the
session and assert that ``test_user`` cannot reach that data.
"""

from app.domains.auth.models import User
from app.domains.leads.models import Lead
from app.domains.projects.models import Project

PROJECTS = "/api/v1/projects"


def _create_project(client, name="Prospects") -> int:
    return client.post(PROJECTS, json={"name": name}).json()["id"]


def _item(place_id, name, **extra):
    return {"place_id": place_id, "name": name, **extra}


def test_save_dedup_and_list(client):
    """Save 2 results -> list shows 2; re-save one + a new one -> only new saved."""
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"

    response = client.post(
        base,
        json={"items": [_item("p1", "Alpha Cafe"), _item("p2", "Beta Bar")]},
    )
    assert response.status_code == 201
    result = response.json()
    assert len(result["saved"]) == 2
    assert result["skipped_place_ids"] == []

    assert len(client.get(base).json()) == 2

    # re-save one existing + one new -> only the new one is saved
    response = client.post(
        base,
        json={"items": [_item("p1", "Alpha Cafe"), _item("p3", "Gamma Grill")]},
    )
    assert response.status_code == 201
    result = response.json()
    assert [lead["place_id"] for lead in result["saved"]] == ["p3"]
    assert result["skipped_place_ids"] == ["p1"]

    # total is 3, no IntegrityError surfaced
    assert len(client.get(base).json()) == 3


def test_save_dedups_within_a_single_batch(client):
    """A place_id repeated inside one request is saved once and skipped once."""
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"

    result = client.post(
        base,
        json={"items": [_item("dup", "First"), _item("dup", "Second")]},
    ).json()
    assert [lead["place_id"] for lead in result["saved"]] == ["dup"]
    assert result["skipped_place_ids"] == ["dup"]
    assert len(client.get(base).json()) == 1


def test_place_ids_endpoint(client):
    """The place-ids endpoint returns the ids already saved in the project."""
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"
    client.post(base, json={"items": [_item("p1", "A"), _item("p2", "B")]})

    place_ids = client.get(f"{base}/place-ids").json()
    assert sorted(place_ids) == ["p1", "p2"]


def test_status_and_name_filters_combine(client):
    """The status filter and the case-insensitive name search work and combine."""
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"
    client.post(
        base,
        json={
            "items": [
                _item("p1", "Downtown Diner"),
                _item("p2", "Uptown Deli"),
                _item("p3", "Riverside Diner"),
            ]
        },
    )
    # mark two as contacted
    leads = {lead["place_id"]: lead["id"] for lead in client.get(base).json()}
    client.patch(f"/api/v1/leads/{leads['p1']}", json={"status": "contacted"})
    client.patch(f"/api/v1/leads/{leads['p3']}", json={"status": "contacted"})

    # status filter
    contacted = client.get(f"{base}?status=contacted").json()
    assert {lead["place_id"] for lead in contacted} == {"p1", "p3"}

    # case-insensitive name search
    diners = client.get(f"{base}?q=diner").json()
    assert {lead["place_id"] for lead in diners} == {"p1", "p3"}

    # combined: contacted AND name contains "diner"
    combined = client.get(f"{base}?status=contacted&q=downtown").json()
    assert {lead["place_id"] for lead in combined} == {"p1"}


def test_get_and_update_lead(client):
    """A lead can be fetched and have its status/linkedin_url updated."""
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"
    lead_id = client.post(base, json={"items": [_item("p1", "Acme")]}).json()["saved"][0]["id"]

    assert client.get(f"/api/v1/leads/{lead_id}").json()["status"] == "new"

    response = client.patch(
        f"/api/v1/leads/{lead_id}",
        json={"status": "interested", "linkedin_url": "https://linkedin.com/company/acme"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "interested"
    assert body["linkedin_url"] == "https://linkedin.com/company/acme"


def test_update_rejects_invalid_status(client):
    """PATCH with a status outside the allowed set returns 422."""
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"
    lead_id = client.post(base, json={"items": [_item("p1", "Acme")]}).json()["saved"][0]["id"]

    assert client.patch(f"/api/v1/leads/{lead_id}", json={"status": "bogus"}).status_code == 422
    # the stored status is unchanged
    assert client.get(f"/api/v1/leads/{lead_id}").json()["status"] == "new"


def test_ownership_is_enforced(client, db_session):
    """Another user's project and lead are invisible and return 404."""
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

    other_base = f"{PROJECTS}/{other_project.id}/leads"

    # collection routes on a project the caller does not own -> 404
    assert client.get(other_base).status_code == 404
    assert client.get(f"{other_base}/place-ids").status_code == 404
    assert client.post(other_base, json={"items": [_item("x", "X")]}).status_code == 404

    # item routes on a lead the caller does not own -> 404
    assert client.get(f"/api/v1/leads/{other_lead.id}").status_code == 404
    assert client.patch(
        f"/api/v1/leads/{other_lead.id}", json={"status": "contacted"}
    ).status_code == 404

    # the other user's lead is untouched
    db_session.refresh(other_lead)
    assert other_lead.status == "new"
    assert other_lead.name == "Confidential"
