from fastapi import APIRouter

from app.routes.admin import router as admin_router
from app.routes.agent import router as agent_router
from app.routes.auth import router as auth_router
from app.routes.batch import router as batch_router
from app.routes.candidates import router as candidates_router
from app.routes.certificates import router as certificates_router
from app.routes.compare import router as compare_router
from app.routes.dashboard import router as dashboard_router
from app.routes.documents import router as documents_router
from app.routes.health import router as health_router
from app.routes.institution import router as institution_router
from app.routes.notifications import router as notifications_router
from app.routes.public import router as public_router
from app.routes.research import router as research_router
from app.routes.reviews import router as reviews_router
from app.routes.settings import router as settings_router
from app.routes.verification import router as verification_router
from app.routes.version import router as version_router
from app.routes.workspaces import router as workspaces_router

api_router = APIRouter()
api_router.include_router(admin_router)
api_router.include_router(agent_router)
api_router.include_router(auth_router)
api_router.include_router(batch_router)
api_router.include_router(candidates_router)
api_router.include_router(certificates_router)
api_router.include_router(compare_router)
api_router.include_router(dashboard_router)
api_router.include_router(documents_router)
api_router.include_router(health_router, tags=["health"])
api_router.include_router(institution_router)
api_router.include_router(notifications_router)
api_router.include_router(public_router)
api_router.include_router(research_router)
api_router.include_router(reviews_router)
api_router.include_router(settings_router)
api_router.include_router(verification_router)
api_router.include_router(version_router, tags=["version"])
api_router.include_router(workspaces_router)
