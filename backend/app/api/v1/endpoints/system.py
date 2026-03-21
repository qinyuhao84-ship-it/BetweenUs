from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.system import RuntimeStatusResponse
from app.services.container import asr_service, llm_service

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/runtime-status", response_model=RuntimeStatusResponse)
def runtime_status() -> RuntimeStatusResponse:
    settings = get_settings()
    return RuntimeStatusResponse(
        ai_provider_mode=settings.ai_provider_mode,
        asr_provider=settings.asr_provider,
        asr_mock_enabled=asr_service.is_mock_enabled(),
        llm_mock_enabled=llm_service.is_mock_enabled(),
        queue_eager_mode=settings.celery_task_always_eager,
    )
