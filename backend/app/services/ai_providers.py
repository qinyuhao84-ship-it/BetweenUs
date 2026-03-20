import json
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.schemas.report import ReportDraft, ReportDraftTask


class ProviderError(RuntimeError):
    pass


class ASRService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def transcribe(self, audio_path: str) -> str:
        if self._use_mock():
            return "用户重复提到希望被理解，并担心对方承诺总是落空。"

        if not self.settings.asr_api_key:
            raise ProviderError("ASR 服务未配置，请先设置 ASR_API_KEY")

        target = Path(audio_path)
        if not target.exists():
            raise ProviderError("音频文件不存在，无法转写")

        try:
            with target.open("rb") as f:
                files = {"file": (target.name, f, "application/octet-stream")}
                data = {
                    "model": self.settings.asr_model,
                    "language": self.settings.asr_language,
                    "response_format": "json",
                }
                response = httpx.post(
                    f"{self.settings.asr_base_url.rstrip('/')}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.settings.asr_api_key}"},
                    data=data,
                    files=files,
                    timeout=self.settings.provider_timeout_seconds,
                )
        except httpx.HTTPError as exc:
            raise ProviderError("ASR 网络请求失败，请稍后重试") from exc

        if response.status_code >= 400:
            raise ProviderError(self._read_remote_error(response, "ASR"))

        payload = response.json()
        transcript = str(payload.get("text", "")).strip()
        if not transcript:
            raise ProviderError("ASR 未返回可用文本")
        return transcript

    def _use_mock(self) -> bool:
        mode = self.settings.ai_provider_mode
        if mode == "mock":
            return True
        if mode == "auto" and not self.settings.asr_api_key:
            return True
        return False

    @staticmethod
    def _read_remote_error(response: httpx.Response, name: str) -> str:
        try:
            payload = response.json()
        except json.JSONDecodeError:
            return f"{name} 服务响应异常，状态码 {response.status_code}"

        detail = payload.get("error")
        if isinstance(detail, dict):
            message = str(detail.get("message", "")).strip()
            if message:
                return f"{name} 服务异常：{message}"
        if isinstance(detail, str) and detail.strip():
            return f"{name} 服务异常：{detail.strip()}"
        return f"{name} 服务响应异常，状态码 {response.status_code}"


class LLMService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate_report(self, transcript: str) -> ReportDraft:
        if self._use_mock():
            return ReportDraft(
                summary="冲突核心是双方都想被重视，但表达方式让对方只听到了指责。",
                potential_needs=["被认真倾听", "承诺有明确时间点"],
                repair_suggestions=["先复述再表达感受", "把承诺改成具体时间和动作"],
                action_tasks=[
                    ReportDraftTask(content="今晚 22:00 前进行 10 分钟轮流表达，不打断"),
                    ReportDraftTask(content="明天 12:00 前共同确认一条可执行的小约定"),
                ],
            )

        if not self.settings.llm_api_key:
            raise ProviderError("LLM 服务未配置，请先设置 LLM_API_KEY 或 DEEPSEEK_API_KEY")

        system_prompt = (
            "你是情侣冲突复盘助手。"
            "请基于转写文本输出严格 JSON，不要输出 markdown。"
            "JSON 结构必须是："
            '{"summary":"...",'
            '"potential_needs":["..."],'
            '"repair_suggestions":["..."],'
            '"action_tasks":[{"content":"..."}]}'
        )
        user_prompt = (
            "请给出中文复盘，要求务实可执行。\n"
            f"转写文本：\n{transcript}\n"
        )
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        try:
            response = httpx.post(
                f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                json=payload,
                timeout=self.settings.provider_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise ProviderError("LLM 网络请求失败，请稍后重试") from exc

        if response.status_code >= 400:
            raise ProviderError(ASRService._read_remote_error(response, "LLM"))

        content = self._extract_content(response.json())
        return self._parse_report(content)

    def _use_mock(self) -> bool:
        mode = self.settings.ai_provider_mode
        if mode == "mock":
            return True
        if mode == "auto" and not self.settings.llm_api_key:
            return True
        return False

    @staticmethod
    def _extract_content(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderError("LLM 未返回候选答案")
        first = choices[0]
        if not isinstance(first, dict):
            raise ProviderError("LLM 响应结构异常")
        message = first.get("message")
        if not isinstance(message, dict):
            raise ProviderError("LLM 响应结构异常")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("LLM 返回内容为空")
        return content

    def _parse_report(self, raw_content: str) -> ReportDraft:
        try:
            payload = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ProviderError("LLM 返回内容不是合法 JSON") from exc

        if not isinstance(payload, dict):
            raise ProviderError("LLM JSON 结构异常")

        summary = str(payload.get("summary", "")).strip()
        if not summary:
            raise ProviderError("LLM 缺少 summary 字段")

        potential_needs = self._normalize_string_list(payload.get("potential_needs"))
        repair_suggestions = self._normalize_string_list(payload.get("repair_suggestions"))
        action_tasks = self._normalize_action_tasks(payload.get("action_tasks"))

        if not potential_needs:
            raise ProviderError("LLM 缺少 potential_needs")
        if not repair_suggestions:
            raise ProviderError("LLM 缺少 repair_suggestions")
        if not action_tasks:
            raise ProviderError("LLM 缺少 action_tasks")

        return ReportDraft(
            summary=summary[:300],
            potential_needs=potential_needs[:5],
            repair_suggestions=repair_suggestions[:5],
            action_tasks=[ReportDraftTask(content=item.content[:120]) for item in action_tasks[:5]],
        )

    @staticmethod
    def _normalize_string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        items: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                items.append(text)
        return items

    @staticmethod
    def _normalize_action_tasks(value: Any) -> list[ReportDraftTask]:
        if not isinstance(value, list):
            return []
        tasks: list[ReportDraftTask] = []
        for item in value:
            if isinstance(item, dict):
                text = str(item.get("content", "")).strip()
            else:
                text = str(item).strip()
            if text:
                tasks.append(ReportDraftTask(content=text))
        return tasks
