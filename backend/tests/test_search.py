"""Tests for the search domain service and router.

A fake ``PlacesClient`` is injected via the ``get_places_client`` dependency
override, so no real API calls happen. The ``client`` fixture (see
``conftest.py``) is authenticated as ``test_user``; ownership tests seed a
second user's project directly on the session.
"""

import pytest

from app.domains.auth.models import User
from app.domains.leads.models import Lead
from app.domains.projects.models import Project
from app.domains.search.places_client import PlacesClientError
from app.domains.search.router import get_places_client
from app.main import app

PROJECTS = "/api/v1/projects"


class FakePlacesClient:
    """A stand-in Places client returning canned, normalized results.

    Records the arguments of the last call so tests can assert dispatch.
    """

    def __init__(self, results=None, error: str | None = None):
        self._results = results or []
        self._error = error
        self.text_calls = []
        self.nearby_calls = []

    def text_search(self, keyword, location_text):
        self.text_calls.append((keyword, location_text))
        if self._error:
            raise PlacesClientError(self._error)
        return list(self._results)

    def nearby_search(self, keyword, lat, lng, radius_m):
        self.nearby_calls.append((keyword, lat, lng, radius_m))
        if self._error:
            raise PlacesClientError(self._error)
        return list(self._results)


def _place(place_id, name="Business", **extra):
    return {
        "place_id": place_id,
        "name": name,
        "address": "1 Main St",
        "phone": "+1 555 0001",
        "website": "https://example.com",
        "category": "restaurant",
        "lat": 40.0,
        "lng": -3.0,
        **extra,
    }


@pytest.fixture
def use_places_client():
    """Install a fake Places client and yield a setter for its canned results."""
    holder = {}

    def _set(**kwargs):
        holder["client"] = FakePlacesClient(**kwargs)
        return holder["client"]

    app.dependency_overrides[get_places_client] = lambda: holder["client"]
    yield _set
    app.dependency_overrides.pop(get_places_client, None)


def _create_project(client, name="Prospects") -> int:
    return client.post(PROJECTS, json={"name": name}).json()["id"]


def test_text_search_records_row_and_returns_results(client, use_places_client, db_session):
    fake = use_places_client(results=[_place("p1"), _place("p2")])
    project_id = _create_project(client)

    response = client.post(
        f"{PROJECTS}/{project_id}/searches",
        json={"keyword": "coffee", "location_type": "text", "location_text": "Berlin"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["result_count"] == 2
    assert body["already_saved_count"] == 0
    assert [r["place_id"] for r in body["results"]] == ["p1", "p2"]
    assert all(r["already_saved"] is False for r in body["results"])

    # The query combined keyword + location_text for the text endpoint.
    assert fake.text_calls == [("coffee", "Berlin")]
    assert fake.nearby_calls == []

    # A Search row was persisted with the right count and params.
    from app.domains.search.models import Search

    row = db_session.query(Search).filter(Search.project_id == project_id).one()
    assert row.result_count == 2
    assert row.location_type == "text"
    assert row.params == {"location_text": "Berlin"}
    assert row.id == body["search_id"]

    # The raw normalized results are snapshotted verbatim (no already_saved flag),
    # and result_count matches the stored list length.
    assert row.results == [_place("p1"), _place("p2")]
    assert row.result_count == len(row.results)
    assert all("already_saved" not in place for place in row.results)


def test_point_search_converts_radius_and_records_row(client, use_places_client, db_session):
    fake = use_places_client(results=[_place("p1")])
    project_id = _create_project(client)

    response = client.post(
        f"{PROJECTS}/{project_id}/searches",
        json={
            "keyword": "restaurant",
            "location_type": "point",
            "lat": 40.4,
            "lng": -3.7,
            "radius_km": 2,
        },
    )
    assert response.status_code == 201
    assert response.json()["result_count"] == 1

    # radius_km was converted to metres for the client.
    assert fake.nearby_calls == [("restaurant", 40.4, -3.7, 2000.0)]
    assert fake.text_calls == []

    from app.domains.search.models import Search

    row = db_session.query(Search).filter(Search.project_id == project_id).one()
    assert row.location_type == "point"
    assert row.params == {"lat": 40.4, "lng": -3.7, "radius_km": 2}

    # A point search likewise snapshots its raw results.
    assert row.results == [_place("p1")]
    assert row.result_count == len(row.results)


def test_already_saved_marks_results_saved_as_leads(client, use_places_client, test_user, db_session):
    use_places_client(results=[_place("p1"), _place("p2"), _place("p3")])
    project_id = _create_project(client)

    # Pre-seed p2 as an existing lead in this project.
    db_session.add(
        Lead(project_id=project_id, user_id=test_user.id, place_id="p2", name="Beta")
    )
    db_session.commit()

    body = client.post(
        f"{PROJECTS}/{project_id}/searches",
        json={"keyword": "coffee", "location_type": "text", "location_text": "Berlin"},
    ).json()

    assert body["already_saved_count"] == 1
    saved_flags = {r["place_id"]: r["already_saved"] for r in body["results"]}
    assert saved_flags == {"p1": False, "p2": True, "p3": False}


def test_history_newest_first_and_ownership(client, use_places_client, test_user, db_session):
    use_places_client(results=[_place("p1")])
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/searches"

    client.post(base, json={"keyword": "one", "location_type": "text", "location_text": "A"})
    client.post(base, json={"keyword": "two", "location_type": "text", "location_text": "B"})

    history = client.get(base).json()
    assert [h["keyword"] for h in history] == ["two", "one"]
    assert all(h["project_id"] == project_id for h in history)

    # Another user's project is not reachable.
    other = User(
        name="Other",
        email="other@example.com",
        hashed_password="x",
        is_verified=True,
    )
    db_session.add(other)
    db_session.commit()
    other_project = Project(user_id=other.id, name="Theirs")
    db_session.add(other_project)
    db_session.commit()

    assert client.get(f"{PROJECTS}/{other_project.id}/searches").status_code == 404
    assert (
        client.post(
            f"{PROJECTS}/{other_project.id}/searches",
            json={"keyword": "x", "location_type": "text", "location_text": "Z"},
        ).status_code
        == 404
    )


def test_invalid_location_fields_rejected(client, use_places_client):
    use_places_client(results=[])
    project_id = _create_project(client)
    base = f"{PROJECTS}/{project_id}/searches"

    # text search without location_text
    assert client.post(base, json={"keyword": "k", "location_type": "text"}).status_code == 422
    # point search missing coordinates
    assert (
        client.post(
            base, json={"keyword": "k", "location_type": "point", "lat": 40.0}
        ).status_code
        == 422
    )


def test_places_client_error_surfaces_as_502(client, use_places_client, db_session):
    use_places_client(error="upstream boom")
    project_id = _create_project(client)

    response = client.post(
        f"{PROJECTS}/{project_id}/searches",
        json={"keyword": "coffee", "location_type": "text", "location_text": "Berlin"},
    )
    assert response.status_code == 502

    # No Search row is recorded when the client fails.
    from app.domains.search.models import Search

    assert db_session.query(Search).count() == 0
