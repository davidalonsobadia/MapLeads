from typing import List, Optional

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.auth.models import User
from app.domains.auth.utils import get_verified_user
from app.domains.search.places_client import PlacesClient

from . import schemas, service

# Searches live under a project, so this router declares full paths rather than
# a single prefix (mirroring the leads router).
router = APIRouter(tags=["search"])


def get_places_client() -> PlacesClient:
    """Provide a Places client. Overridden in tests to inject a fake."""
    return PlacesClient()


@router.post(
    "/search/anonymous",
    response_model=schemas.AnonymousSearchResponse,
)
def run_anonymous_search(
    data: schemas.SearchRequest,
    db: Session = Depends(get_db),
    places_client: PlacesClient = Depends(get_places_client),
    x_anonymous_search_token: Optional[str] = Header(default=None),
):
    """Run a search for an anonymous visitor: capped, contact-masked, persists nothing.

    No user authentication and no project — the endpoint still sits behind the
    ``x-api-key`` gateway like every other ``/api`` route. A visitor replays the
    ``X-Anonymous-Search-Token`` from a previous response; a valid one means the
    single free search is spent and the request is rejected with 403.
    """
    return service.AnonymousSearchService(db, places_client).run_search(
        data, x_anonymous_search_token
    )


@router.post(
    "/projects/{project_id}/searches",
    response_model=schemas.SearchRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_search(
    project_id: int,
    data: schemas.SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
    places_client: PlacesClient = Depends(get_places_client),
):
    """Run a search under a project and return the results. Does not save leads."""
    return service.SearchService(db, places_client).run_search(
        current_user.id, project_id, data
    )


@router.get(
    "/projects/{project_id}/searches",
    response_model=List[schemas.SearchHistoryItem],
)
def list_searches(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
    places_client: PlacesClient = Depends(get_places_client),
):
    """List a project's search history, newest first. Ownership enforced."""
    return service.SearchService(db, places_client).list_searches(
        current_user.id, project_id
    )


# Item routes are declared after the collection routes above so the fixed
# "/searches" path is matched before the "{search_id}" parameter route.
@router.get(
    "/projects/{project_id}/searches/{search_id}",
    response_model=schemas.SearchRunResponse,
)
def get_search(
    project_id: int,
    search_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
    places_client: PlacesClient = Depends(get_places_client),
):
    """Return a stored search's snapshot. Served from history, no Places re-query."""
    return service.SearchService(db, places_client).get_search(
        current_user.id, project_id, search_id
    )


@router.delete(
    "/projects/{project_id}/searches/{search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_search(
    project_id: int,
    search_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
    places_client: PlacesClient = Depends(get_places_client),
):
    """Delete a stored search from a project's history. Ownership enforced."""
    service.SearchService(db, places_client).delete_search(
        current_user.id, project_id, search_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
