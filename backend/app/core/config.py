from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BetweenUs API"
    env: str = "dev"
    database_url: str = "sqlite:///./betweenus.db"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    asr_provider: str = "openai_compatible"
    asr_api_key: str = ""
    asr_base_url: str = "https://api.openai.com/v1"
    asr_model: str = "whisper-1"
    asr_language: str = "zh"
    asr_volc_app_id: str = ""
    asr_volc_access_token: str = ""
    asr_volc_resource_id: str = "volc.seedasr.auc"
    asr_volc_submit_url: str = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
    asr_volc_query_url: str = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"
    asr_volc_upload_provider: str = "none"
    asr_poll_seconds: float = 2.0
    asr_poll_max_attempts: int = 120
    ai_provider_mode: str = "auto"
    provider_timeout_seconds: int = 60
    max_audio_file_bytes: int = 25 * 1024 * 1024
    recording_storage_dir: str = "./storage/recordings"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_always_eager: bool = False
    max_processing_minutes: int = 10
    default_subscription_units: int = 6
    jwt_secret_key: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    allow_insecure_header_auth: bool = False
    sms_provider: str = "mock"
    sms_http_endpoint: str = ""
    sms_http_auth_token: str = ""
    sms_template: str = "【BetweenUs】验证码 {code}，5 分钟内有效。"
    sms_code_expires_seconds: int = 300
    sms_send_interval_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        if self.llm_api_key == "" and self.deepseek_api_key != "":
            self.llm_api_key = self.deepseek_api_key
        if self.llm_base_url == "":
            self.llm_base_url = self.deepseek_base_url
        if self.llm_model == "":
            self.llm_model = self.deepseek_model

        if self.ai_provider_mode not in {"real", "mock", "auto"}:
            raise ValueError("AI_PROVIDER_MODE 只支持 real / mock / auto")
        if self.asr_provider not in {"openai_compatible", "volc_recording_bigmodel"}:
            raise ValueError("ASR_PROVIDER 只支持 openai_compatible / volc_recording_bigmodel")
        if self.asr_volc_upload_provider not in {"none", "catbox", "tmpfiles"}:
            raise ValueError("ASR_VOLC_UPLOAD_PROVIDER 只支持 none / catbox / tmpfiles")
        if (
            self.ai_provider_mode == "real"
            and self.asr_provider == "volc_recording_bigmodel"
            and (not self.asr_volc_app_id or not self.asr_volc_access_token)
        ):
            raise ValueError("使用火山录音识别时必须配置 ASR_VOLC_APP_ID 与 ASR_VOLC_ACCESS_TOKEN")

        if self.env not in {"dev", "test"} and self.jwt_secret_key == "change-me-in-prod":
            raise ValueError("生产环境必须配置 JWT_SECRET_KEY")
        if self.env not in {"dev", "test"} and not self.database_url.startswith("postgresql"):
            raise ValueError("生产环境必须使用 PostgreSQL 数据库地址")
        if self.sms_provider not in {"mock", "http"}:
            raise ValueError("SMS_PROVIDER 只支持 mock / http")
        if self.sms_provider == "http" and not self.sms_http_endpoint:
            raise ValueError("SMS_PROVIDER=http 时必须配置 SMS_HTTP_ENDPOINT")
        if self.sms_code_expires_seconds < 60:
            raise ValueError("SMS_CODE_EXPIRES_SECONDS 不能小于 60")
        if self.sms_send_interval_seconds < 30:
            raise ValueError("SMS_SEND_INTERVAL_SECONDS 不能小于 30")
        if self.env not in {"dev", "test"} and self.sms_provider == "mock":
            raise ValueError("生产环境不允许 SMS_PROVIDER=mock，请改为 http 并接入真实短信网关")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
