from pydantic import BaseModel


class RuntimeStatusResponse(BaseModel):
    ai_provider_mode: str
    asr_provider: str
    asr_mock_enabled: bool
    llm_mock_enabled: bool
    queue_eager_mode: bool
