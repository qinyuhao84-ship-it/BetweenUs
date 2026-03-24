import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_current_user_id
from app.schemas.common import ProgressSnapshot
from app.schemas.session import (
    CreateSessionRequest,
    FinishSessionRequest,
    FinishSessionResponse,
    SessionDetailResponse,
    SessionResponse,
    UpdateSessionTitleRequest,
    UploadSessionAudioResponse,
)
from app.services.container import audio_storage_service, billing_service, progress_service, session_service
from app.workers.tasks import process_session_task

router = APIRouter(prefix="/sessions", tags=["sessions"])
logger = logging.getLogger(__name__)


@router.post("", response_model=SessionResponse)
def create_session(payload: CreateSessionRequest, user_id: str = Depends(get_current_user_id)) -> SessionResponse:
    record = session_service.create_session(user_id=user_id, title=payload.title)
    billing_service.get_or_create(user_id)
    return SessionResponse(
        session_id=record.session_id,
        title=record.title,
        status=record.status,
        created_at=record.created_at,
    )


@router.post("/{session_id}/finish", response_model=FinishSessionResponse)
def finish_session(
    session_id: str,
    payload: FinishSessionRequest,
    user_id: str = Depends(get_current_user_id),
) -> FinishSessionResponse:
    if not payload.consent_acknowledged:
        raise HTTPException(status_code=400, detail="录音前置声明未确认")

    try:
        record = session_service.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="会话不存在") from exc

    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问该会话")
    if record.status != "recording":
        raise HTTPException(status_code=409, detail="会话已结束，不能重复提交")
    if not record.audio_file_path:
        raise HTTPException(status_code=400, detail="请先上传录音文件")

    settlement = billing_service.settle(user_id=user_id, duration_minutes=payload.duration_minutes)
    if not settlement.approved:
        raise HTTPException(status_code=402, detail=f"余额不足，缺少 {settlement.shortage_units} 单位")

    session_service.finish(session_id=session_id, duration_minutes=payload.duration_minutes)
    progress_service.start(session_id)
    try:
        process_session_task.apply_async(args=[session_id], ignore_result=True, retry=False)
    except Exception as enqueue_exc:  # noqa: BLE001
        logger.exception("failed to enqueue pipeline task for session %s: %s", session_id, enqueue_exc)
        session_service.fail(session_id, "任务系统暂时不可用，请稍后重试")
        progress_service.fail(session_id)
        raise HTTPException(status_code=503, detail="任务系统暂时不可用，请稍后重试") from enqueue_exc

    progress = progress_service.get(session_id)
    status = "completed" if progress.stage == "completed" else "processing"

    return FinishSessionResponse(
        session_id=session_id,
        status=status,
        progress=ProgressSnapshot(stage=progress.stage, percent=progress.percent, updated_at=progress.updated_at),
    )


@router.post("/{session_id}/audio", response_model=UploadSessionAudioResponse)
async def upload_session_audio(
    session_id: str,
    audio_file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
) -> UploadSessionAudioResponse:
    try:
        record = session_service.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="会话不存在") from exc

    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问该会话")
    if record.status != "recording":
        raise HTTPException(status_code=409, detail="会话已结束，不能重复上传录音")

    try:
        stored_path, stored_bytes = await audio_storage_service.save_upload(session_id, audio_file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_service.attach_audio(session_id=session_id, audio_file_path=stored_path)
    return UploadSessionAudioResponse(session_id=session_id, uploaded=True, bytes_received=stored_bytes)


@router.get("", response_model=list[SessionResponse])
def list_sessions(user_id: str = Depends(get_current_user_id)) -> list[SessionResponse]:
    items = session_service.list_by_user(user_id)
    return [
        SessionResponse(session_id=item.session_id, title=item.title, status=item.status, created_at=item.created_at)
        for item in sorted(items, key=lambda x: x.created_at, reverse=True)
    ]


@router.patch("/{session_id}/title", response_model=SessionDetailResponse)
def update_session_title(
    session_id: str,
    payload: UpdateSessionTitleRequest,
    user_id: str = Depends(get_current_user_id),
) -> SessionDetailResponse:
    try:
        record = session_service.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="会话不存在") from exc

    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问该会话")

    try:
        updated = session_service.update_title(session_id, payload.title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    transcript_excerpt = updated.transcript_text.strip()
    if len(transcript_excerpt) > 280:
        transcript_excerpt = transcript_excerpt[:280] + "..."

    return SessionDetailResponse(
        session_id=updated.session_id,
        title=updated.title,
        status=updated.status,
        created_at=updated.created_at,
        duration_minutes=updated.duration_minutes,
        failure_reason=updated.failure_reason,
        transcript_excerpt=transcript_excerpt,
    )


@router.get("/{session_id}/progress", response_model=ProgressSnapshot)
def get_progress(session_id: str, user_id: str = Depends(get_current_user_id)) -> ProgressSnapshot:
    try:
        record = session_service.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="会话不存在") from exc

    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问该会话")

    progress = progress_service.get(session_id)
    return ProgressSnapshot(stage=progress.stage, percent=progress.percent, updated_at=progress.updated_at)


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(session_id: str, user_id: str = Depends(get_current_user_id)) -> SessionDetailResponse:
    try:
        record = session_service.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="会话不存在") from exc

    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问该会话")

    transcript_excerpt = record.transcript_text.strip()
    if len(transcript_excerpt) > 280:
        transcript_excerpt = transcript_excerpt[:280] + "..."

    return SessionDetailResponse(
        session_id=record.session_id,
        title=record.title,
        status=record.status,
        created_at=record.created_at,
        duration_minutes=record.duration_minutes,
        failure_reason=record.failure_reason,
        transcript_excerpt=transcript_excerpt,
    )
