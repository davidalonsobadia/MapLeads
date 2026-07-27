"""Tests for the account-wide lead stats endpoint.

The ``client`` fixture is authenticated as ``test_user`` (see ``conftest.py``).
The ownership test seeds a second user and their leads directly on the session
and asserts they never contribute to ``test_user``'s stats.
"""

from app.domains.auth.models import User
from app.domains.leads.models import Lead
from app.domains.projects.models import Project

PROJECTS = "/api/v1/projects"
STATS = "/api/v1/leads/stats"


def _create_project(client, name="Prospects") -> int:
    return client.post(PROJECTS, json={"name": name}).json()["id"]


def _item(place_id, name, **extra):
    return {"place_id": place_id, "name": name, **extra}


def test_stats_empty(client):
    """A user with no leads gets all zeros with 200 (not 404)."""
    response = client.get(STATS)
    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "new": 0,
        "contacted": 0,
        "interested": 0,
        "discarded": 0,
    }


def test_stats_counts_by_status(client):
    """Saved leads PATCHed to different statuses are counted per status."""
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/leads"
    client.post(
        base,
        json={
            "items": [
                _item("p1", "A"),
                _item("p2", "B"),
                _item("p3", "C"),
                _item("p4", "D"),
                _item("p5", "E"),
            ]
        },
    )
    leads = {lead["place_id"]: lead["id"] for lead in client.get(base).json()}
    client.patch(f"/api/v1/leads/{leads['p2']}", json={"status": "contacted"})
    client.patch(f"/api/v1/leads/{leads['p3']}", json={"status": "contacted"})
    client.patch(f"/api/v1/leads/{leads['p4']}", json={"status": "interested"})
    client.patch(f"/api/v1/leads/{leads['p5']}", json={"status": "discarded"})

    body = client.get(STATS).json()
    assert body == {
        "total": 5,
        "new": 1,
        "contacted": 2,
        "interested": 1,
        "discarded": 1,
    }
    assert body["total"] == (
        body["new"] + body["contacted"] + body["interested"] + body["discarded"]
    )


def test_stats_spans_multiple_projects(client):
    """Leads under two owned projects roll up into one account-wide total."""
    project_a = _create_project(client, name="Project A")
    project_b = _create_project(client, name="Project B")
    client.post(
        f"{PROJECTS}/{project_a}/leads",
        json={"items": [_item("a1", "A1"), _item("a2", "A2")]},
    )
    client.post(
        f"{PROJECTS}/{project_b}/leads",
        json={"items": [_item("b1", "B1")]},
    )

    body = client.get(STATS).json()
    assert body["total"] == 3
    assert body["new"] == 3


def test_stats_scoped_to_owner(client, db_session):
    """Another user's leads never contribute to the caller's stats."""
    other_user = User(
        name="Other User",
        email="other-stats@example.com",
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

    for place_id, lead_status in (("s1", "new"), ("s2", "contacted")):
        db_session.add(
            Lead(
                project_id=other_project.id,
                user_id=other_user.id,
                place_id=place_id,
                name=f"Other {place_id}",
                status=lead_status,
            )
        )
    db_session.commit()

    # test_user still owns nothing.
    assert client.get(STATS).json() == {
        "total": 0,
        "new": 0,
        "contacted": 0,
        "interested": 0,
        "discarded": 0,
    }


def test_stats_path_not_shadowed_by_lead_item_route(client):
    """GET /leads/stats resolves to the stats route, not /leads/{lead_id}."""
    response = client.get(STATS)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"total", "new", "contacted", "interested", "discarded"}
