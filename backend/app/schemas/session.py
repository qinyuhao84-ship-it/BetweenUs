from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ProgressSnapshot


class CreateSessionRequest(BaseModel):
    title: str = Field(default="冲突复盘", min_length=1, max_length=100)


class SessionResponse(BaseModel):
    session_id: str
    status: str
    created_at: datetime


class FinishSessionRequest(BaseModel):
    duration_minutes: int = Field(ge=1, le=240)
    consent_acknowledged: bool


class FinishSessionResponse(BaseModel):
    session_id: str
    status: str
    progress: ProgressSnapshot


class UploadSessionAudioResponse(BaseModel):
    session_id: str
    uploaded: bool
    bytes_received: int
