from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import init_db
from app.schemas.common import APIMessage

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(api_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/healthz", response_model=APIMessage, tags=["system"])
def healthz() -> APIMessage:
    return APIMessage(message="ok")
