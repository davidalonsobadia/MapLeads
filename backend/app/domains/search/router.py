from typing import List

from fastapi import APIRouter, Depends, status
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
