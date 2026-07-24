from fastapi import APIRouter

from app.api.health import router as health_router
from app.domains.auth.router import router as auth_router
from app.domains.leads.router import router as leads_router
from app.domains.projects.router import router as projects_router
from app.domains.search.router import router as search_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(projects_router)
router.include_router(leads_router)
router.include_router(search_router)
