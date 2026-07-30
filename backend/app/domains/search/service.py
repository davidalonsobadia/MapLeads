from typing import Any, Dict, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.leads.models import Lead
from app.domains.projects.models import Project
from app.domains.search.places_client import PlacesClient, PlacesClientError

from . import anonymous_token, models, schemas

# Metres per kilometre, used to translate the request's radius_km into the
# radius_m the Places client expects.
METRES_PER_KM = 1000.0


def dispatch_search(
    places_client: PlacesClient, req: schemas.SearchRequest
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Call the right Places endpoint and return (persisted params, results).

    Shared by the authenticated and anonymous search flows. A
    ``PlacesClientError`` from the client surfaces as HTTP 502.
    """
    try:
        if req.location_type == "text":
            params: Dict[str, Any] = {"location_text": req.location_text}
            results = places_client.text_search(req.keyword, req.location_text)
        else:  # point
            params = {
                "lat": req.lat,
                "lng": req.lng,
                "radius_km": req.radius_km,
            }
            results = places_client.nearby_search(
                req.keyword,
                req.lat,
                req.lng,
                req.radius_km * METRES_PER_KM,
            )
    except PlacesClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return params, results


class SearchService:
    """Runs searches through the Places client and records project history.

    The client is injected so tests can substitute a fake without any real API
    calls, and ownership is enforced through the parent project.
    """

    def __init__(self, db: Session, places_client: PlacesClient):
        self.db = db
        self.places_client = places_client

    def _get_owned_project(self, user_id: int, project_id: int) -> Project:
        """Return the project if owned by the user, else raise 404."""
        project = (
            self.db.query(Project)
            .filter(Project.id == project_id, Project.user_id == user_id)
            .first()
        )
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    def run_search(
        self, user_id: int, project_id: int, req: schemas.SearchRequest
    ) -> schemas.SearchRunResponse:
        """Run a text or point+radius search, record it, and mark saved results.

        A ``Search`` row is persisted with the result count. Running a search
        never saves leads and never consumes quota; results whose ``place_id`` is
        already a lead in this project are flagged ``already_saved``.
        """
        self._get_owned_project(user_id, project_id)

        params, raw_results = self._dispatch(req)

        search = models.Search(
            project_id=project_id,
            user_id=user_id,
            keyword=req.keyword,
            location_type=req.location_type,
            params=params,
            result_count=len(raw_results),
            results=raw_results,
        )
        self.db.add(search)
        self.db.commit()
        self.db.refresh(search)

        saved_place_ids = self._existing_place_ids(project_id)
        results: List[schemas.SearchResultItem] = []
        already_saved_count = 0
        for place in raw_results:
            already_saved = place.get("place_id") in saved_place_ids
            if already_saved:
                already_saved_count += 1
            results.append(
                schemas.SearchResultItem(**place, already_saved=already_saved)
            )

        return schemas.SearchRunResponse(
            search_id=search.id,
            result_count=len(results),
            already_saved_count=already_saved_count,
            results=results,
        )

    def list_searches(self, user_id: int, project_id: int) -> List[models.Search]:
        """List an owned project's search history, newest first."""
        self._get_owned_project(user_id, project_id)
        return (
            self.db.query(models.Search)
            .filter(
                models.Search.project_id == project_id,
                models.Search.user_id == user_id,
            )
            .order_by(
                models.Search.created_at.desc(),
                models.Search.id.desc(),
            )
            .all()
        )

    def _get_owned_search(
        self, user_id: int, project_id: int, search_id: int
    ) -> models.Search:
        """Return the search under an owned project, else raise 404.

        Ownership is enforced through the parent project first, then the search
        is loaded by ``id`` + ``project_id`` + ``user_id`` so a search that is
        not the caller's (or not under this project) is indistinguishable from a
        missing one — no leak.
        """
        self._get_owned_project(user_id, project_id)
        search = (
            self.db.query(models.Search)
            .filter(
                models.Search.id == search_id,
                models.Search.project_id == project_id,
                models.Search.user_id == user_id,
            )
            .first()
        )
        if search is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Search not found",
            )
        return search

    def get_search(
        self, user_id: int, project_id: int, search_id: int
    ) -> schemas.SearchRunResponse:
        """Return a stored search's snapshot with freshly-recomputed saved flags.

        Served entirely from the persisted snapshot — the Places API is never
        re-queried. ``already_saved`` is recomputed against the project's current
        leads, so a place saved after the search ran is flagged on view. Legacy
        rows (``results IS NULL``, written before snapshots) return an empty list
        with their stored ``result_count``.
        """
        search = self._get_owned_search(user_id, project_id, search_id)

        raw_results = search.results or []
        saved_place_ids = self._existing_place_ids(project_id)
        results: List[schemas.SearchResultItem] = []
        already_saved_count = 0
        for place in raw_results:
            already_saved = place.get("place_id") in saved_place_ids
            if already_saved:
                already_saved_count += 1
            results.append(
                schemas.SearchResultItem(**place, already_saved=already_saved)
            )

        return schemas.SearchRunResponse(
            search_id=search.id,
            result_count=search.result_count,
            already_saved_count=already_saved_count,
            results=results,
        )

    def delete_search(
        self, user_id: int, project_id: int, search_id: int
    ) -> None:
        """Delete an owned search. Raises 404 if not under the owned project."""
        search = self._get_owned_search(user_id, project_id, search_id)
        self.db.delete(search)
        self.db.commit()

    def _dispatch(
        self, req: schemas.SearchRequest
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Call the right Places endpoint and return (persisted params, results)."""
        return dispatch_search(self.places_client, req)

    def _existing_place_ids(self, project_id: int) -> set[str]:
        """Return the set of place_ids already saved as leads in the project."""
        rows = (
            self.db.query(Lead.place_id)
            .filter(Lead.project_id == project_id)
            .all()
        )
        return {row[0] for row in rows}


class AnonymousSearchService:
    """Runs a search for an unauthenticated visitor: capped and contact-masked.

    Unlike ``SearchService`` this persists nothing (no ``Search`` row, no
    ``Lead``) and consumes no subscription quota. Results are capped to
    ``settings.ANONYMOUS_SEARCH_RESULT_LIMIT`` and masked to identity-only
    fields (no phone, website or coordinates). A ``db`` session is accepted for
    signature parity with the other services even though it is unused today.
    """

    def __init__(self, db: Session, places_client: PlacesClient):
        self.db = db
        self.places_client = places_client

    def run_search(
        self, req: schemas.SearchRequest, visitor_token: str | None = None
    ) -> schemas.AnonymousSearchResponse:
        """Run a text or point+radius search and return capped, masked results.

        ``visitor_token`` is the value the caller replayed from a previous
        response. A valid, unexpired token means the search is already spent:
        reject with 403 and never call the Places client. Otherwise run the
        search and hand back a freshly issued token to persist.
        """
        if anonymous_token.verify_token(visitor_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You've used your search. Sign up to keep searching.",
            )

        _, raw_results = dispatch_search(self.places_client, req)

        limit = settings.ANONYMOUS_SEARCH_RESULT_LIMIT
        results = [
            schemas.AnonymousSearchResultItem(
                place_id=place.get("place_id"),
                name=place.get("name"),
                address=place.get("address"),
                category=place.get("category"),
            )
            for place in raw_results[:limit]
        ]

        return schemas.AnonymousSearchResponse(
            result_count=len(results),
            total_available=len(raw_results),
            results=results,
            visitor_token=anonymous_token.issue_token(),
        )
