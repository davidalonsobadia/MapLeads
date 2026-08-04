"""Tests for the Google Places API (New) client wrapper.

All HTTP is mocked with :class:`httpx.MockTransport` - there are no real network
calls. We assert the outgoing request (URL, field-mask header, body), single- and
multi-page parsing, the pagination cap (including the empty-page-with-token
anomaly), and the missing-key error.
"""

import json

import httpx
import pytest

from app.domains.search.places_client import (
    FIELD_MASK,
    MAX_RESULTS,
    PAGE_SIZE,
    PlacesClient,
    PlacesClientError,
)


def _place(i: int) -> dict:
    """A raw Places API place payload for index ``i``."""
    return {
        "id": f"place-{i}",
        "displayName": {"text": f"Business {i}", "languageCode": "en"},
        "formattedAddress": f"{i} Main St",
        "nationalPhoneNumber": f"+1 555 000 {i:04d}",
        "websiteUri": f"https://example.com/{i}",
        "primaryType": "restaurant",
        "types": ["restaurant", "food"],
        "location": {"latitude": 40.0 + i, "longitude": -3.0 - i},
    }


def _client_with_handler(handler, api_key: str = "test-key") -> PlacesClient:
    transport = httpx.MockTransport(handler)
    return PlacesClient(api_key=api_key, http_client=httpx.Client(transport=transport))


def test_text_search_builds_request_and_normalizes():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["field_mask"] = request.headers.get("X-Goog-FieldMask")
        captured["api_key"] = request.headers.get("X-Goog-Api-Key")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"places": [_place(1)]})

    client = _client_with_handler(handler)
    results = client.text_search("coffee", "Berlin")

    assert captured["method"] == "POST"
    assert captured["url"] == "https://places.googleapis.com/v1/places:searchText"
    assert captured["field_mask"] == FIELD_MASK
    assert captured["api_key"] == "test-key"
    assert captured["body"] == {"textQuery": "coffee in Berlin", "pageSize": PAGE_SIZE}

    assert results == [
        {
            "place_id": "place-1",
            "name": "Business 1",
            "address": "1 Main St",
            "phone": "+1 555 000 0001",
            "website": "https://example.com/1",
            "category": "restaurant",
            "lat": 41.0,
            "lng": -4.0,
        }
    ]


def test_text_search_without_location_uses_bare_keyword():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"places": []})

    client = _client_with_handler(handler)
    client.text_search("dentist", "")

    assert captured["body"]["textQuery"] == "dentist"


def test_point_search_builds_request_and_normalizes():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["field_mask"] = request.headers.get("X-Goog-FieldMask")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"places": [_place(2)]})

    client = _client_with_handler(handler)
    results = client.point_search("restaurant", 40.4, -3.7, 1500)

    # Point search goes through Text Search (not Nearby Search) so free-text
    # keywords aren't rejected as invalid place types.
    assert captured["url"] == "https://places.googleapis.com/v1/places:searchText"
    assert captured["field_mask"] == FIELD_MASK
    # The circle goes under ``locationBias`` (a soft bias), not
    # ``locationRestriction`` - Text Search only accepts a rectangle as a hard
    # restriction and 400s on a circular ``locationRestriction``.
    assert captured["body"] == {
        "textQuery": "restaurant",
        "pageSize": PAGE_SIZE,
        "locationBias": {
            "circle": {
                "center": {"latitude": 40.4, "longitude": -3.7},
                "radius": 1500,
            }
        },
    }
    assert results[0]["place_id"] == "place-2"
    assert results[0]["lat"] == 42.0


def test_category_falls_back_to_first_type():
    place = _place(3)
    del place["primaryType"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"places": [place]})

    client = _client_with_handler(handler)
    results = client.text_search("shop", "Madrid")
    assert results[0]["category"] == "restaurant"  # first entry in ``types``


def test_pagination_follows_next_page_token():
    tokens_seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        token = body.get("pageToken")
        tokens_seen.append(token)
        if token is None:
            return httpx.Response(
                200, json={"places": [_place(1)], "nextPageToken": "PAGE2"}
            )
        if token == "PAGE2":
            return httpx.Response(
                200, json={"places": [_place(2)], "nextPageToken": "PAGE3"}
            )
        return httpx.Response(200, json={"places": [_place(3)]})

    client = _client_with_handler(handler)
    results = client.text_search("coffee", "Berlin")

    assert tokens_seen == [None, "PAGE2", "PAGE3"]
    assert [r["place_id"] for r in results] == ["place-1", "place-2", "place-3"]


def test_pagination_stops_at_cap():
    """Even with an endless supply of pages, we never exceed ``MAX_RESULTS``."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        start = (calls["n"] - 1) * PAGE_SIZE
        places = [_place(start + i) for i in range(PAGE_SIZE)]
        # Always advertise another page.
        return httpx.Response(
            200, json={"places": places, "nextPageToken": f"tok-{calls['n']}"}
        )

    client = _client_with_handler(handler)
    results = client.text_search("coffee", "Berlin")

    assert len(results) == MAX_RESULTS
    # 60 results / 20 per page == exactly 3 requests.
    assert calls["n"] == MAX_RESULTS // PAGE_SIZE


def test_pagination_stops_on_empty_pages_with_token():
    """An empty page that still advertises a token must not loop forever."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        # 0 places but a continuation token every time - the anomaly case.
        return httpx.Response(200, json={"places": [], "nextPageToken": "tok"})

    client = _client_with_handler(handler)
    results = client.text_search("coffee", "Berlin")

    assert results == []
    # Bounded by the page-count ceiling, not the (never-reached) result cap.
    assert calls["n"] == MAX_RESULTS // PAGE_SIZE


def test_missing_api_key_raises_descriptive_error():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no request should be sent when the key is missing")

    client = _client_with_handler(handler, api_key="")

    with pytest.raises(PlacesClientError, match="GOOGLE_PLACES_API_KEY"):
        client.text_search("coffee", "Berlin")


def test_api_error_response_is_wrapped():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403, json={"error": {"code": 403, "message": "PERMISSION_DENIED"}}
        )

    client = _client_with_handler(handler)

    with pytest.raises(PlacesClientError, match="403.*PERMISSION_DENIED"):
        client.text_search("coffee", "Berlin")


def test_transport_error_is_wrapped():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client = _client_with_handler(handler)

    with pytest.raises(PlacesClientError, match="request failed"):
        client.text_search("coffee", "Berlin")


def test_context_manager_closes_owned_client():
    """The context manager closes a client it created itself."""
    with PlacesClient(api_key="test-key") as client:
        http_client = client._client  # lazily created and owned by the instance
        assert not http_client.is_closed

    assert http_client.is_closed
    assert client._http_client is None


def test_close_does_not_close_injected_client():
    """A caller-provided client is left open for the caller to manage."""
    injected = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    client = PlacesClient(api_key="test-key", http_client=injected)

    client.close()

    assert not injected.is_closed
    injected.close()
