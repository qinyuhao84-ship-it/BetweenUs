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
    asr_api_key: str = ""
    asr_base_url: str = "https://api.openai.com/v1"
    asr_model: str = "whisper-1"
    asr_language: str = "zh"
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

        if self.env not in {"dev", "test"} and self.jwt_secret_key == "change-me-in-prod":
            raise ValueError("生产环境必须配置 JWT_SECRET_KEY")
        if self.env not in {"dev", "test"} and not self.database_url.startswith("postgresql"):
            raise ValueError("生产环境必须使用 PostgreSQL 数据库地址")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
