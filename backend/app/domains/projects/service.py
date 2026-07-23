from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from . import models, schemas


class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, data: schemas.ProjectCreate) -> models.Project:
        """Create a new project owned by the given user."""
        project = models.Project(user_id=user_id, name=data.name)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def list(self, user_id: int, include_archived: bool = False) -> List[models.Project]:
        """List the projects owned by the user, optionally including archived ones."""
        query = self.db.query(models.Project).filter(models.Project.user_id == user_id)
        if not include_archived:
            query = query.filter(models.Project.archived.is_(False))
        return query.order_by(models.Project.created_at.desc()).all()

    def get(self, user_id: int, project_id: int) -> models.Project:
        """Get a single project owned by the user or raise 404."""
        project = (
            self.db.query(models.Project)
            .filter(models.Project.id == project_id, models.Project.user_id == user_id)
            .first()
        )
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    def update(
        self, user_id: int, project_id: int, data: schemas.ProjectUpdate
    ) -> models.Project:
        """Partially update a project (rename and/or archive) owned by the user."""
        project = self.get(user_id, project_id)
        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(project, field, value)
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, user_id: int, project_id: int) -> None:
        """Delete a project owned by the user or raise 404."""
        project = self.get(user_id, project_id)
        self.db.delete(project)
        self.db.commit()
