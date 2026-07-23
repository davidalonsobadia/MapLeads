from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.auth.models import User
from app.domains.auth.utils import get_verified_user

from . import schemas, service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=schemas.ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    data: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Create a new project owned by the current user."""
    return service.ProjectService(db).create(current_user.id, data)


@router.get("", response_model=List[schemas.ProjectResponse])
def list_projects(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """List the current user's projects, excluding archived ones by default."""
    return service.ProjectService(db).list(current_user.id, include_archived)


@router.get("/{project_id}", response_model=schemas.ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Get one of the current user's projects. Returns 404 if not owned/found."""
    return service.ProjectService(db).get(current_user.id, project_id)


@router.patch("/{project_id}", response_model=schemas.ProjectResponse)
def update_project(
    project_id: int,
    data: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Rename and/or archive one of the current user's projects (partial update)."""
    return service.ProjectService(db).update(current_user.id, project_id, data)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Delete one of the current user's projects. Returns 404 if not owned/found."""
    service.ProjectService(db).delete(current_user.id, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
