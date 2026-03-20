from datetime import datetime

from pydantic import BaseModel


class APIMessage(BaseModel):
    message: str


class APIError(BaseModel):
    detail: str


class ProgressSnapshot(BaseModel):
    stage: str
    percent: int
    updated_at: datetime
