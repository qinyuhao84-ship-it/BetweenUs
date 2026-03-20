import logging

from app.schemas.report import ActionTask, ReportResponse
from app.services.ai_providers import ProviderError
from app.services.container import (
    asr_service,
    audio_storage_service,
    llm_service,
    progress_service,
    session_service,
)

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    @staticmethod
    def run_sync(session_id: str) -> None:
        audio_path = ""
        try:
            session = session_service.get_session(session_id)
            audio_path = session.audio_file_path
            if not audio_path:
                raise ProviderError("录音文件不存在，请重新上传后再试")

            progress_service.advance(session_id, "transcribing", 35)
            transcript = asr_service.transcribe(audio_path)

            progress_service.advance(session_id, "analyzing", 70)
            report_draft = llm_service.generate_report(transcript)

            progress_service.advance(session_id, "rendering", 95)
            report = ReportResponse(
                session_id=session_id,
                summary=report_draft.summary,
                potential_needs=report_draft.potential_needs,
                repair_suggestions=report_draft.repair_suggestions,
                action_tasks=[
                    ActionTask(task_id=f"t-{idx + 1}", content=task.content)
                    for idx, task in enumerate(report_draft.action_tasks)
                ],
            )
            session_service.complete(session_id=session_id, transcript=transcript, report=report)
            progress_service.complete(session_id)
        except ProviderError as exc:
            logger.warning("session %s pipeline provider error: %s", session_id, exc)
            session_service.fail(session_id, str(exc))
            progress_service.fail(session_id)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("session %s pipeline failed", session_id)
            session_service.fail(session_id, "复盘处理失败，请稍后重试")
            progress_service.fail(session_id)
            raise
        finally:
            audio_storage_service.cleanup(audio_path)

