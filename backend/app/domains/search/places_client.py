"""Thin wrapper around the Google Places API (New).

This module exposes :class:`PlacesClient`, a small, testable HTTP client built
on a single search endpoint, ``places:searchText``, used for both of MapLeads'
search modes:

* ``text_search``  - a free-text keyword plus a free-text location.
* ``point_search`` - a free-text keyword biased to a circle (point + radius).

Both go through Text Search rather than Nearby Search because Nearby Search
filters by place *type* (a fixed Google enum, e.g. ``"restaurant"``) and
rejects arbitrary keywords with a 400 - MapLeads' keyword field is always free
text, so ``point_search`` uses Text Search's ``locationBias`` circle to
get the same point+radius semantics without that restriction. Text Search only
accepts a circle under ``locationBias`` (a soft bias); ``locationRestriction``
supports a rectangle only, so a circular ``locationRestriction`` is rejected
with a 400 (``Unknown name "circle" at 'location_restriction'``).

Only the **Basic Data** field set is requested (via the ``X-Goog-FieldMask``
header) to keep responses cheap, and pagination is followed up to the API cap of
~60 results. Each raw place is normalized to a flat ``dict`` so callers never
touch the Google response shape directly.

No HTTP endpoints or persistence live here - that is intentionally out of scope
for this task (see the epic). This is a plain library used by future services.
"""

from __future__ import annotations

from typing import Any

import httpx

from app import logger
from app.core.config import settings

# Places API (New) base URL and endpoint path. Both search modes below go
# through Text Search - see the module docstring for why.
PLACES_API_BASE_URL = "https://places.googleapis.com/v1"
TEXT_SEARCH_PATH = "/places:searchText"

# The API returns at most 20 results per page and caps pagination at 3 pages,
# i.e. ~60 results in total. We expose the cap as a constant so callers/tests can
# reason about it explicitly.
PAGE_SIZE = 20
MAX_RESULTS = 60

# Basic Data fields only, plus ``location`` (Basic tier) so we can surface
# coordinates, and ``nextPageToken`` so we can follow pagination.
_PLACE_FIELDS = (
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
    "places.websiteUri",
    "places.primaryType",
    "places.types",
    "places.location",
)
FIELD_MASK = ",".join((*_PLACE_FIELDS, "nextPageToken"))

# Default request timeout in seconds.
DEFAULT_TIMEOUT = 30.0


class PlacesClientError(RuntimeError):
    """Raised when the Places API is misconfigured or returns an error.

    Using a dedicated exception lets callers turn upstream failures into a
    meaningful HTTP response instead of leaking a raw 500.
    """


class PlacesClient:
    """Client for the Google Places API (New).

    Parameters
    ----------
    api_key:
        Google Maps Platform key with "Places API (New)" enabled. Defaults to
        ``settings.GOOGLE_PLACES_API_KEY``.
    http_client:
        Optional pre-built :class:`httpx.Client` (useful for tests). When not
        supplied, a client is created lazily and owned by this instance.
    """

    def __init__(
        self,
        api_key: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.GOOGLE_PLACES_API_KEY
        self._http_client = http_client
        self._owns_client = http_client is None

    # -- public API ---------------------------------------------------------

    def text_search(self, keyword: str, location_text: str) -> list[dict[str, Any]]:
        """Run a Text Search and return normalized place dicts.

        ``keyword`` and ``location_text`` are combined into a single free-text
        query (e.g. ``"coffee in Berlin"``).
        """
        query = keyword.strip()
        location_text = (location_text or "").strip()
        if location_text:
            query = f"{query} in {location_text}"

        body = {"textQuery": query, "pageSize": PAGE_SIZE}
        return self._paginate(TEXT_SEARCH_PATH, body)

    def point_search(
        self,
        keyword: str,
        lat: float,
        lng: float,
        radius_m: float,
    ) -> list[dict[str, Any]]:
        """Run a Text Search biased to a circle of ``radius_m`` metres
        around ``lat``/``lng``.

        ``keyword`` stays free text, just like :meth:`text_search` - only the
        location is expressed differently (a circle instead of a place name).

        The circle is sent under ``locationBias`` rather than
        ``locationRestriction`` because Text Search only supports a circular
        shape as a soft bias; ``locationRestriction`` accepts a rectangle only
        and 400s on a circle. A bias is the closest Text Search behaviour to a
        point+radius search.
        """
        body = {
            "textQuery": keyword.strip(),
            "pageSize": PAGE_SIZE,
            "locationBias": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": radius_m,
                }
            },
        }
        return self._paginate(TEXT_SEARCH_PATH, body)

    # -- internals ----------------------------------------------------------

    def _paginate(self, path: str, body: dict[str, Any]) -> list[dict[str, Any]]:
        """POST ``body`` to ``path``, following ``nextPageToken`` up to the cap.

        The page count is hard-bounded by ``MAX_RESULTS // PAGE_SIZE`` so that an
        upstream anomaly (e.g. an empty page that still advertises a
        ``nextPageToken``) can never trigger unbounded network requests.
        """
        results: list[dict[str, Any]] = []
        request_body = dict(body)
        max_pages = MAX_RESULTS // PAGE_SIZE

        for _ in range(max_pages):
            payload = self._post(path, request_body)
            for place in payload.get("places", []) or []:
                results.append(_normalize_place(place))
                if len(results) >= MAX_RESULTS:
                    return results

            next_token = payload.get("nextPageToken")
            if not next_token:
                return results
            request_body = {**body, "pageToken": next_token}

        return results

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise PlacesClientError(
                "GOOGLE_PLACES_API_KEY is not configured; set it in the environment "
                "to use the Places API."
            )

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        }
        url = f"{PLACES_API_BASE_URL}{path}"

        try:
            response = self._client.post(url, json=body, headers=headers)
        except httpx.HTTPError as exc:  # network/transport failure
            logger.error("Places API request failed: %s", exc)
            raise PlacesClientError(f"Places API request failed: {exc}") from exc

        if response.status_code >= 400:
            detail = _error_detail(response)
            logger.error("Places API returned %s: %s", response.status_code, detail)
            raise PlacesClientError(
                f"Places API error {response.status_code}: {detail}"
            )

        return response.json()

    @property
    def _client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=DEFAULT_TIMEOUT)
        return self._http_client

    def close(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._owns_client and self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> PlacesClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _normalize_place(place: dict[str, Any]) -> dict[str, Any]:
    """Flatten a raw Places API place into MapLeads' canonical shape."""
    location = place.get("location") or {}
    display_name = place.get("displayName") or {}
    category = place.get("primaryType")
    if not category:
        types = place.get("types") or []
        category = types[0] if types else None

    return {
        "place_id": place.get("id"),
        "name": display_name.get("text"),
        "address": place.get("formattedAddress"),
        "phone": place.get("nationalPhoneNumber"),
        "website": place.get("websiteUri"),
        "category": category,
        "lat": location.get("latitude"),
        "lng": location.get("longitude"),
    }


def _error_detail(response: httpx.Response) -> str:
    """Extract a human-readable message from a Places API error response."""
    try:
        payload = response.json()
    except ValueError:
        return response.text or "unknown error"
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])
    return str(payload)
