from app.core.config import get_settings
from app.services.ai_providers import ASRService, LLMService
from app.services.audio_storage import AudioStorageService
from app.services.auth_service import AuthService
from app.services.billing_service import BillingService
from app.services.progress import ProgressService
from app.services.session_service import SessionService

settings = get_settings()
auth_service = AuthService()
billing_service = BillingService()
progress_service = ProgressService()
session_service = SessionService()
audio_storage_service = AudioStorageService(
    base_dir=settings.recording_storage_dir,
    max_audio_file_bytes=settings.max_audio_file_bytes,
)
asr_service = ASRService(settings=settings)
llm_service = LLMService(settings=settings)
