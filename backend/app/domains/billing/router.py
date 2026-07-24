from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.auth.models import User
from app.domains.auth.utils import get_verified_user

from . import schemas
from .service import SubscriptionService

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("", response_model=schemas.SubscriptionUsage)
def get_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """Return the current user's plan and usage, including quota remaining and
    trial days left."""
    return SubscriptionService(db).usage(current_user.id)
