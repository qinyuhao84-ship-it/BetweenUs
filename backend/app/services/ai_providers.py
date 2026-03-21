import json
import subprocess
import time
import uuid
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

        if self.settings.asr_provider == "volc_recording_bigmodel":
            return self._transcribe_with_volc(audio_path)
        return self._transcribe_with_openai(audio_path)

    def is_mock_enabled(self) -> bool:
        return self._use_mock()

    def _transcribe_with_openai(self, audio_path: str) -> str:
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

    def _transcribe_with_volc(self, audio_path: str) -> str:
        if not self.settings.asr_volc_app_id or not self.settings.asr_volc_access_token:
            raise ProviderError("豆包录音识别未配置，请先设置 ASR_VOLC_APP_ID 与 ASR_VOLC_ACCESS_TOKEN")

        target = Path(audio_path)
        audio_url = self._resolve_audio_url(audio_path, target)
        request_id = str(uuid.uuid4())
        headers = {
            "Content-Type": "application/json",
            "X-Api-App-Key": self.settings.asr_volc_app_id,
            "X-Api-Access-Key": self.settings.asr_volc_access_token,
            "X-Api-Resource-Id": self.settings.asr_volc_resource_id,
            "X-Api-Request-Id": request_id,
            "X-Api-Sequence": "-1",
        }
        payload = {
            "user": {"uid": "betweenus-user"},
            "audio": {
                "url": audio_url,
                "format": self._guess_audio_format(target, audio_url),
                "language": self._normalize_asr_language(self.settings.asr_language),
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
            },
        }

        try:
            submit_response = httpx.post(
                self.settings.asr_volc_submit_url,
                headers=headers,
                json=payload,
                timeout=self.settings.provider_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise ProviderError("豆包 ASR 提交任务失败，请稍后重试") from exc

        if submit_response.status_code >= 400:
            raise ProviderError(self._read_remote_error(submit_response, "豆包 ASR"))

        submit_code = self._parse_volc_status_code(submit_response)
        if submit_code != 20000000:
            message = self._extract_volc_message(submit_response)
            raise ProviderError(f"豆包 ASR 提交失败：{message}")

        query_headers = {k: v for k, v in headers.items() if k != "X-Api-Sequence"}
        for _ in range(self.settings.asr_poll_max_attempts):
            try:
                query_response = httpx.post(
                    self.settings.asr_volc_query_url,
                    headers=query_headers,
                    json={},
                    timeout=self.settings.provider_timeout_seconds,
                )
            except httpx.HTTPError as exc:
                raise ProviderError("豆包 ASR 查询结果失败，请稍后重试") from exc

            if query_response.status_code >= 400:
                raise ProviderError(self._read_remote_error(query_response, "豆包 ASR"))

            query_code = self._parse_volc_status_code(query_response)
            if query_code == 20000000:
                transcript = self._parse_volc_result_text(query_response)
                if not transcript:
                    raise ProviderError("豆包 ASR 返回成功，但文本为空")
                return transcript
            if query_code in {20000001, 20000002}:
                time.sleep(self.settings.asr_poll_seconds)
                continue
            if query_code == 20000003:
                raise ProviderError("豆包 ASR 检测到静音音频，请重新录制")

            message = self._extract_volc_message(query_response)
            raise ProviderError(f"豆包 ASR 查询失败：{message}")

        raise ProviderError("豆包 ASR 处理超时，请稍后重试")

    def _resolve_audio_url(self, audio_path: str, target: Path) -> str:
        if audio_path.startswith("http://") or audio_path.startswith("https://"):
            return audio_path
        if not target.exists():
            raise ProviderError("音频文件不存在，无法转写")
        if self.settings.asr_volc_upload_provider == "catbox":
            return self._upload_to_catbox(target)
        if self.settings.asr_volc_upload_provider == "tmpfiles":
            return self._upload_to_tmpfiles(target)
        raise ProviderError(
            "豆包录音识别模型要求公网可访问的音频 URL。"
            "请先把音频放到可外网访问的对象存储，或在开发环境将 ASR_VOLC_UPLOAD_PROVIDER 设置为 catbox / tmpfiles。"
        )

    def _upload_to_catbox(self, target: Path) -> str:
        last_error = "上传音频到临时公网地址失败，请检查网络"
        for attempt in range(3):
            try:
                result = subprocess.run(
                    [
                        "curl",
                        "--http1.1",
                        "-sS",
                        "-F",
                        "reqtype=fileupload",
                        "-F",
                        f"fileToUpload=@{target}",
                        "https://catbox.moe/user/api.php",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=self.settings.provider_timeout_seconds,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                last_error = str(exc).strip() or "上传音频到临时公网地址失败，请稍后重试"
                if attempt < 2:
                    time.sleep(1)
                    continue
                raise ProviderError("上传音频到临时公网地址失败，请稍后重试") from exc

            if result.returncode == 0:
                url = (result.stdout or "").strip()
                if url.startswith("http://") or url.startswith("https://"):
                    return url
                last_error = "临时音频上传失败，请改用对象存储 URL"
            else:
                detail = (result.stderr or "").strip()
                if detail:
                    last_error = f"上传音频到临时公网地址失败：{detail}"
                else:
                    last_error = "上传音频到临时公网地址失败，请检查网络"

            if attempt < 2:
                time.sleep(1)

        raise ProviderError(last_error)

    def _upload_to_tmpfiles(self, target: Path) -> str:
        last_error = "上传音频到 tmpfiles 失败，请检查网络"
        for attempt in range(3):
            try:
                result = subprocess.run(
                    [
                        "curl",
                        "--http1.1",
                        "-sS",
                        "-F",
                        f"file=@{target}",
                        "https://tmpfiles.org/api/v1/upload",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=self.settings.provider_timeout_seconds,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                last_error = str(exc).strip() or "上传音频到 tmpfiles 失败，请稍后重试"
                if attempt < 2:
                    time.sleep(1)
                    continue
                raise ProviderError("上传音频到 tmpfiles 失败，请稍后重试") from exc

            if result.returncode == 0:
                try:
                    payload = json.loads((result.stdout or "").strip() or "{}")
                except json.JSONDecodeError:
                    payload = {}
                url = ""
                if isinstance(payload, dict):
                    data = payload.get("data")
                    if isinstance(data, dict):
                        raw_url = str(data.get("url", "")).strip()
                        if raw_url.startswith("http://") or raw_url.startswith("https://"):
                            if "/dl/" in raw_url:
                                url = raw_url
                            else:
                                url = raw_url.replace("://tmpfiles.org/", "://tmpfiles.org/dl/")
                if url.startswith("http://") or url.startswith("https://"):
                    return url
                last_error = "tmpfiles 返回了无效链接，请改用对象存储 URL"
            else:
                detail = (result.stderr or "").strip()
                if detail:
                    last_error = f"上传音频到 tmpfiles 失败：{detail}"
                else:
                    last_error = "上传音频到 tmpfiles 失败，请检查网络"

            if attempt < 2:
                time.sleep(1)

        raise ProviderError(last_error)

    @staticmethod
    def _normalize_asr_language(language: str) -> str:
        if language == "zh":
            return "zh-CN"
        return language

    @staticmethod
    def _guess_audio_format(target: Path, audio_url: str) -> str:
        suffix = target.suffix.lower().lstrip(".")
        if not suffix:
            suffix = audio_url.rsplit(".", 1)[-1].lower() if "." in audio_url else ""
        if suffix in {"wav", "mp3", "ogg", "raw", "aac", "webm"}:
            return suffix
        if suffix in {"m4a", "mp4"}:
            return "mp4"
        return "wav"

    @staticmethod
    def _parse_volc_status_code(response: httpx.Response) -> int:
        code_raw = response.headers.get("X-Api-Status-Code", "").strip()
        if code_raw.isdigit():
            return int(code_raw)
        try:
            payload = response.json()
        except json.JSONDecodeError:
            raise ProviderError("豆包 ASR 响应格式异常")
        if isinstance(payload, dict):
            header = payload.get("header")
            if isinstance(header, dict):
                code = header.get("code")
                try:
                    return int(code)
                except (TypeError, ValueError):
                    pass
        raise ProviderError("豆包 ASR 未返回状态码")

    @staticmethod
    def _extract_volc_message(response: httpx.Response) -> str:
        from_header = response.headers.get("X-Api-Message", "").strip()
        if from_header:
            return from_header
        try:
            payload = response.json()
        except json.JSONDecodeError:
            return f"HTTP {response.status_code}"
        if isinstance(payload, dict):
            header = payload.get("header")
            if isinstance(header, dict):
                message = str(header.get("message", "")).strip()
                if message:
                    return message
            error = payload.get("error")
            if isinstance(error, dict):
                message = str(error.get("message", "")).strip()
                if message:
                    return message
        return f"HTTP {response.status_code}"

    @staticmethod
    def _parse_volc_result_text(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError("豆包 ASR 结果不是合法 JSON") from exc
        if not isinstance(payload, dict):
            return ""
        result = payload.get("result")
        if isinstance(result, dict):
            text = str(result.get("text", "")).strip()
            if text:
                return text
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict):
                text = str(first.get("text", "")).strip()
                if text:
                    return text
        return str(payload.get("text", "")).strip()

    def _use_mock(self) -> bool:
        mode = self.settings.ai_provider_mode
        if mode == "mock":
            return True
        if mode == "auto":
            if self.settings.asr_provider == "volc_recording_bigmodel":
                return not (self.settings.asr_volc_app_id and self.settings.asr_volc_access_token)
            return not self.settings.asr_api_key
        return False

    @staticmethod
    def _read_remote_error(response: httpx.Response, name: str) -> str:
        message = response.headers.get("X-Api-Message", "").strip()
        if message:
            return f"{name} 服务异常：{message}"
        try:
            payload = response.json()
        except json.JSONDecodeError:
            return f"{name} 服务响应异常，状态码 {response.status_code}"

        header = payload.get("header")
        if isinstance(header, dict):
            message = str(header.get("message", "")).strip()
            if message:
                return f"{name} 服务异常：{message}"

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
            "你是“关系修复复盘教练”，不是裁判。"
            "你的目标是把一段冲突对话拆成可理解、可执行、可复盘的关系修复方案。"
            "禁止输出评判输赢、道德指责或谁该被教育。"
            "请严格遵循："
            "1) summary 使用四段结构并打上小标题："
            "【冲突主线】、【双方表述】、【深层诉求】、【当前卡点】；"
            "2) 【双方表述】必须同时写出 A 方和 B 方“说了什么 + 真正在意什么”；"
            "3) potential_needs 至少 4 条，且必须覆盖双方，建议格式："
            "“A方显性表达：...；A方隐含诉求：...”或“B方...”；"
            "4) repair_suggestions 至少 4 条，要求具体到话术或动作，避免“多沟通”这类空话；"
            "5) action_tasks 至少 3 条，必须可验证，包含时间锚点、触发条件或完成标准；"
            "6) 若信息不足，明确写“基于现有信息的保守推断”，不要臆造事实。"
            "输出必须是严格 JSON，不要 markdown，不要解释，不要额外字段。"
            "JSON 结构固定为："
            '{"summary":"...",'
            '"potential_needs":["..."],'
            '"repair_suggestions":["..."],'
            '"action_tasks":[{"content":"..."}]}'
        )
        user_prompt = (
            "请基于以下转写内容生成中文复盘报告。"
            "你要像资深产品经理+关系教练那样组织信息，让用户读完后立刻知道："
            "双方到底在争什么、真正怕什么、误会卡在哪里、下一步怎么做。"
            "重点提炼：冲突触发点、双方表述、深层诉求、误读链路、可立即执行的修复动作。\n"
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

        response: httpx.Response | None = None
        last_http_error: Exception | None = None
        for attempt in range(3):
            try:
                response = httpx.post(
                    f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                    json=payload,
                    timeout=self.settings.provider_timeout_seconds,
                )
            except httpx.HTTPError as exc:
                last_http_error = exc
                if attempt < 2:
                    time.sleep(1.2 * (attempt + 1))
                    continue
                break

            if response.status_code in {429} or response.status_code >= 500:
                if attempt < 2:
                    time.sleep(1.2 * (attempt + 1))
                    continue

            break

        if response is None:
            raise ProviderError("LLM 网络请求失败，请稍后重试") from last_http_error

        if response.status_code >= 400:
            raise ProviderError(ASRService._read_remote_error(response, "LLM"))

        content = self._extract_content(response.json())
        return self._parse_report(content)

    def is_mock_enabled(self) -> bool:
        return self._use_mock()

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
            summary=summary[:900],
            potential_needs=potential_needs[:8],
            repair_suggestions=repair_suggestions[:8],
            action_tasks=[ReportDraftTask(content=item.content[:180]) for item in action_tasks[:6]],
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
