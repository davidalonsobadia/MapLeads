"""Tests for the unauthenticated anonymous search endpoint.

The endpoint runs a real search through the injected Places client but persists
nothing and consumes no quota. Results are capped and contact-masked. A fake
``PlacesClient`` is injected via the ``get_places_client`` dependency override,
reusing the pattern from ``test_search.py``. No project or authenticated user is
required, so tests POST to the endpoint directly.
"""

import pytest

from app.core.config import settings
from app.domains.leads.models import Lead
from app.domains.search.models import Search
from app.domains.search.router import get_places_client
from app.main import app
from tests.test_search import FakePlacesClient, _place

ANONYMOUS = "/api/v1/search/anonymous"


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


def test_anonymous_search_masks_contact_fields(client, use_places_client):
    use_places_client(results=[_place("p1")])

    response = client.post(
        ANONYMOUS,
        json={"keyword": "coffee", "location_type": "text", "location_text": "Berlin"},
    )
    assert response.status_code == 200
    item = response.json()["results"][0]

    assert item == {
        "place_id": "p1",
        "name": "Business",
        "address": "1 Main St",
        "category": "restaurant",
    }
    # Contact and coordinate fields are dropped from the payload, not just the UI.
    assert "phone" not in item
    assert "website" not in item
    assert "lat" not in item
    assert "lng" not in item
    assert "already_saved" not in item


def test_anonymous_search_caps_results(client, use_places_client):
    limit = settings.ANONYMOUS_SEARCH_RESULT_LIMIT
    fake = use_places_client(
        results=[_place(f"p{i}") for i in range(limit + 2)]
    )

    body = client.post(
        ANONYMOUS,
        json={"keyword": "coffee", "location_type": "text", "location_text": "Berlin"},
    ).json()

    assert len(body["results"]) == limit
    assert body["result_count"] == limit
    # total_available reflects the full, pre-capping count from the client.
    assert body["total_available"] == limit + 2
    assert fake.text_calls == [("coffee", "Berlin")]


def test_anonymous_point_search_converts_radius(client, use_places_client):
    fake = use_places_client(results=[_place("p1")])

    response = client.post(
        ANONYMOUS,
        json={
            "keyword": "restaurant",
            "location_type": "point",
            "lat": 40.4,
            "lng": -3.7,
            "radius_km": 2,
        },
    )
    assert response.status_code == 200
    assert response.json()["total_available"] == 1
    # radius_km was converted to metres and dispatched to nearby_search.
    assert fake.nearby_calls == [("restaurant", 40.4, -3.7, 2000.0)]
    assert fake.text_calls == []


def test_anonymous_search_persists_nothing(client, use_places_client, db_session):
    use_places_client(results=[_place("p1"), _place("p2")])

    client.post(
        ANONYMOUS,
        json={"keyword": "coffee", "location_type": "text", "location_text": "Berlin"},
    )

    assert db_session.query(Search).count() == 0
    assert db_session.query(Lead).count() == 0


def test_anonymous_search_invalid_request_422(client, use_places_client):
    use_places_client(results=[])

    # text search without location_text
    assert (
        client.post(
            ANONYMOUS, json={"keyword": "k", "location_type": "text"}
        ).status_code
        == 422
    )
    # point search missing coordinates
    assert (
        client.post(
            ANONYMOUS, json={"keyword": "k", "location_type": "point", "lat": 40.0}
        ).status_code
        == 422
    )


def test_anonymous_search_client_error_502(client, use_places_client):
    use_places_client(error="upstream boom")

    response = client.post(
        ANONYMOUS,
        json={"keyword": "coffee", "location_type": "text", "location_text": "Berlin"},
    )
    assert response.status_code == 502
