from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BetweenUs API"
    env: str = "prod"
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
    asr_volc_upload_provider: str = "volc_tos"
    volc_tos_endpoint: str = ""
    volc_tos_region: str = ""
    volc_tos_bucket: str = ""
    volc_tos_access_key_id: str = ""
    volc_tos_access_key_secret: str = ""
    volc_tos_key_prefix: str = "betweenus-audio"
    volc_tos_presign_expires_seconds: int = 900
    asr_poll_seconds: float = 2.0
    asr_poll_max_attempts: int = 120
    ai_provider_mode: str = "real"
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
    apple_client_id: str = ""
    apple_sign_in_audience: str = ""
    apple_team_id: str = ""
    apple_key_id: str = ""
    apple_private_key: str = ""
    apple_jwks_url: str = "https://appleid.apple.com/auth/keys"
    apple_token_url: str = "https://appleid.apple.com/auth/token"
    apple_revoke_url: str = "https://appleid.apple.com/auth/revoke"
    sms_provider: str = "aliyun"
    sms_aliyun_access_key_id: str = ""
    sms_aliyun_access_key_secret: str = ""
    sms_aliyun_endpoint: str = "dypnsapi.aliyuncs.com"
    sms_aliyun_sign_name: str = ""
    sms_aliyun_template_code: str = ""
    sms_aliyun_scheme_name: str = ""
    sms_template: str = "【BetweenUs】验证码 {code}，5 分钟内有效。"
    sms_code_expires_seconds: int = 300
    sms_send_interval_seconds: int = 60
    apple_iap_bundle_id: str = ""
    apple_iap_environment: str = "production"
    apple_iap_app_apple_id: int | None = None
    apple_iap_root_ca_paths: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        if self.llm_api_key == "" and self.deepseek_api_key != "":
            self.llm_api_key = self.deepseek_api_key
        if self.llm_base_url == "":
            self.llm_base_url = self.deepseek_base_url
        if self.llm_model == "":
            self.llm_model = self.deepseek_model

        if self.ai_provider_mode not in {"real", "mock"}:
            raise ValueError("AI_PROVIDER_MODE 只支持 real / mock")
        if self.asr_provider not in {"openai_compatible", "volc_recording_bigmodel"}:
            raise ValueError("ASR_PROVIDER 只支持 openai_compatible / volc_recording_bigmodel")
        if self.asr_volc_upload_provider not in {"none", "volc_tos"}:
            raise ValueError("ASR_VOLC_UPLOAD_PROVIDER 只支持 none / volc_tos")
        if self.env != "test" and self.ai_provider_mode != "real":
            raise ValueError("非测试环境必须使用 AI_PROVIDER_MODE=real")
        if self.ai_provider_mode == "real":
            if not self.llm_api_key:
                raise ValueError("真实链路必须配置 LLM_API_KEY 或 DEEPSEEK_API_KEY")
            if self.asr_provider == "volc_recording_bigmodel":
                if not self.asr_volc_app_id or not self.asr_volc_access_token:
                    raise ValueError("使用火山录音识别时必须配置 ASR_VOLC_APP_ID 与 ASR_VOLC_ACCESS_TOKEN")
                if self.env != "test" and self.asr_volc_upload_provider != "volc_tos":
                    raise ValueError("火山录音识别正式链路必须配置 ASR_VOLC_UPLOAD_PROVIDER=volc_tos")
                if self.asr_volc_upload_provider == "volc_tos" and (
                    not self.volc_tos_endpoint
                    or not self.volc_tos_region
                    or not self.volc_tos_bucket
                    or not self.volc_tos_access_key_id
                    or not self.volc_tos_access_key_secret
                ):
                    raise ValueError("使用火山录音识别时必须配置完整的火山 TOS 存储参数")
            elif not self.asr_api_key:
                raise ValueError("使用 openai_compatible ASR 时必须配置 ASR_API_KEY")

        if self.env != "test" and self.jwt_secret_key == "change-me-in-prod":
            raise ValueError("非测试环境必须配置真实 JWT_SECRET_KEY")
        if self.env != "test" and not self.database_url.startswith("postgresql"):
            raise ValueError("非测试环境必须使用 PostgreSQL 数据库地址")
        if self.env != "test":
            if not self.apple_client_id:
                raise ValueError("非测试环境必须配置 APPLE_CLIENT_ID")
            if not self.apple_sign_in_audience:
                self.apple_sign_in_audience = self.apple_client_id
            if not self.apple_team_id or not self.apple_key_id or not self.apple_private_key:
                raise ValueError("非测试环境必须配置 Apple 登录密钥信息")
            if not self.apple_iap_bundle_id:
                raise ValueError("非测试环境必须配置 APPLE_IAP_BUNDLE_ID")
            if self.apple_iap_environment not in {"local_testing", "sandbox", "production"}:
                raise ValueError("APPLE_IAP_ENVIRONMENT 只支持 local_testing / sandbox / production")
            if self.apple_iap_environment in {"sandbox", "production"} and not self.apple_iap_root_ca_paths.strip():
                raise ValueError("正式验签 Apple IAP 时必须配置 APPLE_IAP_ROOT_CA_PATHS")
            if self.apple_iap_environment == "production" and self.apple_iap_app_apple_id is None:
                raise ValueError("APPLE_IAP_ENVIRONMENT=production 时必须配置 APPLE_IAP_APP_APPLE_ID")
        elif not self.apple_sign_in_audience:
            self.apple_sign_in_audience = self.apple_client_id or "com.betweenus.app"
        if self.sms_provider not in {"mock", "aliyun"}:
            raise ValueError("SMS_PROVIDER 只支持 mock / aliyun")
        if self.sms_provider == "aliyun":
            if not self.sms_aliyun_access_key_id or not self.sms_aliyun_access_key_secret:
                raise ValueError("SMS_PROVIDER=aliyun 时必须配置阿里云 AccessKey")
            if not self.sms_aliyun_sign_name or not self.sms_aliyun_template_code:
                raise ValueError("SMS_PROVIDER=aliyun 时必须配置短信签名与模板")
        if self.sms_code_expires_seconds < 60:
            raise ValueError("SMS_CODE_EXPIRES_SECONDS 不能小于 60")
        if self.sms_send_interval_seconds < 30:
            raise ValueError("SMS_SEND_INTERVAL_SECONDS 不能小于 30")
        if self.env != "test" and self.sms_provider != "aliyun":
            raise ValueError("非测试环境不允许 SMS_PROVIDER=mock，请改为 aliyun")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
