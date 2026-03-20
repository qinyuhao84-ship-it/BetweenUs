from fastapi import APIRouter

from app.api.v1.endpoints import auth, billing, reports, sessions

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(sessions.router)
api_router.include_router(reports.router)
api_router.include_router(billing.router)
