from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user_id
from app.schemas.report import ReportResponse
from app.services.container import session_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{session_id}", response_model=ReportResponse)
def get_report(session_id: str, user_id: str = Depends(get_current_user_id)) -> ReportResponse:
    try:
        record = session_service.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="会话不存在") from exc

    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问该会话")

    if record.status == "failed":
        raise HTTPException(status_code=409, detail=record.failure_reason or "复盘任务失败")

    if record.status != "completed":
        raise HTTPException(status_code=409, detail="报告尚未生成")

    try:
        return session_service.get_report(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="报告不存在") from exc
