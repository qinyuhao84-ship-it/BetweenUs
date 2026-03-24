from fastapi import FastAPI
from sqlalchemy import text
from sqlmodel import Session

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import engine, init_db
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


@app.get("/readyz", response_model=APIMessage, tags=["system"])
def readyz() -> APIMessage:
    with Session(engine) as session:
        session.exec(text("SELECT 1"))
    return APIMessage(message="ready")
