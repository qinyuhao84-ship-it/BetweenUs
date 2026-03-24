import mimetypes
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import boto3
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
        audio_url, cleanup_remote = self._resolve_audio_source(audio_path, target)
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
        finally:
            cleanup_remote()

    def _resolve_audio_source(self, audio_path: str, target: Path) -> tuple[str, Callable[[], None]]:
        if audio_path.startswith("http://") or audio_path.startswith("https://"):
            return audio_path, lambda: None
        if not target.exists():
            raise ProviderError("音频文件不存在，无法转写")
        if self.settings.asr_volc_upload_provider == "volc_tos":
            audio_url, object_key = self._upload_to_volc_tos(target)
            return audio_url, lambda: self._cleanup_remote_audio(object_key)
        raise ProviderError(
            "豆包录音识别模型要求公网可访问的音频 URL。"
            "请先把音频放到火山 TOS，或直接传入可访问的 HTTPS 音频地址。"
        )

    def _upload_to_volc_tos(self, target: Path) -> tuple[str, str]:
        key_prefix = self.settings.volc_tos_key_prefix.strip().strip("/")
        object_key = f"{key_prefix}/{uuid.uuid4().hex}{target.suffix.lower()}" if key_prefix else f"{uuid.uuid4().hex}{target.suffix.lower()}"
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        try:
            client = boto3.client(
                "s3",
                endpoint_url=self._normalize_tos_endpoint(self.settings.volc_tos_endpoint),
                region_name=self.settings.volc_tos_region,
                aws_access_key_id=self.settings.volc_tos_access_key_id,
                aws_secret_access_key=self.settings.volc_tos_access_key_secret,
            )
            client.upload_file(
                Filename=str(target),
                Bucket=self.settings.volc_tos_bucket,
                Key=object_key,
                ExtraArgs={"ContentType": content_type},
            )
            presigned_url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.settings.volc_tos_bucket, "Key": object_key},
                ExpiresIn=self.settings.volc_tos_presign_expires_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError("上传音频到火山 TOS 失败，请检查存储配置") from exc

        if not presigned_url.startswith(("http://", "https://")):
            raise ProviderError("火山 TOS 预签名地址无效")
        return presigned_url, object_key

    def _cleanup_remote_audio(self, object_key: str) -> None:
        if not object_key:
            return
        try:
            client = boto3.client(
                "s3",
                endpoint_url=self._normalize_tos_endpoint(self.settings.volc_tos_endpoint),
                region_name=self.settings.volc_tos_region,
                aws_access_key_id=self.settings.volc_tos_access_key_id,
                aws_secret_access_key=self.settings.volc_tos_access_key_secret,
            )
            client.delete_object(Bucket=self.settings.volc_tos_bucket, Key=object_key)
        except Exception:
            return

    @staticmethod
    def _normalize_tos_endpoint(endpoint: str) -> str:
        value = endpoint.strip()
        if value.startswith("http://") or value.startswith("https://"):
            return value
        return f"https://{value}"

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
        return self.settings.env == "test" and self.settings.ai_provider_mode == "mock"

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
                potential_needs=[
                    "A方显性表达：希望立刻解决问题；A方隐含诉求：被当作重要优先级",
                    "A方显性表达：不想再重复同一争论；A方隐含诉求：关系里有确定性",
                    "B方显性表达：不想被命令和指责；B方隐含诉求：被尊重表达边界",
                    "B方显性表达：希望有缓冲时间；B方隐含诉求：情绪被看见并允许修复节奏",
                ],
                repair_suggestions=[
                    "开场先用 30 秒复述对方意思，再说自己的感受，避免直接反驳",
                    "把“你总是”改成“当 X 发生时，我会担心 Y”",
                    "每次冲突只解决一个议题，其他议题放进待办清单",
                    "约定冲突暂停词，触发后先冷静 15 分钟再继续沟通",
                ],
                action_tasks=[
                    ReportDraftTask(content="今晚 22:00 前进行 10 分钟轮流表达，不打断"),
                    ReportDraftTask(content="明天 12:00 前共同确认一条可执行的小约定"),
                    ReportDraftTask(content="本周末前复盘一次“哪些表达让你感觉被理解”"),
                ],
                detailed_report=(
                    "【1. 情绪动态与触发点】\n"
                    "A方在对话中主要呈现焦虑+愤怒混合情绪，触发点是“承诺不确定”；"
                    "B方主要呈现防御+委屈，触发点是“被否定感”。\n\n"
                    "【2. 双方心理需求与防御机制】\n"
                    "A方核心需求是稳定与可预期，防御机制偏向控制与追问；"
                    "B方核心需求是被尊重与被接纳，防御机制偏向回避与沉默。\n\n"
                    "【3. 沟通失真链路】\n"
                    "A方的“催促”被B方听成“否定”，B方的“沉默”被A方听成“不在乎”，"
                    "双方都在保护自己，但彼此接收到的是攻击信号。\n\n"
                    "【4. 关系风险评估】\n"
                    "短期风险是高频重复争执；中期风险是情绪账户透支；长期风险是关系意义感下降。\n\n"
                    "【5. 修复策略】\n"
                    "短期先止损（暂停词+轮流表达），中期建立沟通节奏（固定每周关系对话），"
                    "长期建立共同问题解决模板（议题澄清-需求表达-行动确认-回看）。\n\n"
                    "【6. 建议话术】\n"
                    "A方可说：我现在急不是想压你，而是我在害怕事情又悬着；"
                    "B方可说：我不是不在乎，我需要先整理情绪才能好好回应你。\n\n"
                    "【7. 自我调节练习】\n"
                    "冲突前做 60 秒呼吸和身体扫描；冲突后各自写下“我真正担心的是什么”。\n\n"
                    "【8. 下次复盘观察指标】\n"
                    "是否减少打断、是否出现复述、是否形成可验证的小承诺、是否按约回看。"
                ),
            )

        if not self.settings.llm_api_key:
            raise ProviderError("LLM 服务未配置，请先设置 LLM_API_KEY 或 DEEPSEEK_API_KEY")

        system_prompt = """
你是“亲密关系冲突复盘分析师 + 情绪教练”，不是裁判，不负责判定谁对谁错。
你的任务是基于对话文本，输出高质量、可执行、可复盘的关系修复分析。

【硬性目标】
1) 保持中立：不站队、不道德评判、不贴人格标签。
2) 心理深度：分析双方显性诉求、隐性诉求、防御机制、误读链路。
3) 行动导向：给出可立即执行、可验证的步骤和话术。
4) 证据意识：每个关键判断尽量对应对话证据；信息不足时明确“保守推断”。
5) 安全边界：不得输出临床诊断，不替代专业医疗/法律建议。

【输出格式要求】
必须只输出 JSON，不要 Markdown，不要额外解释，不要多余字段。
JSON 必须严格包含以下字段：
{
  "summary": "四段结构：\\n【冲突主线】...\\n【双方表述】...\\n【深层诉求】...\\n【当前卡点】...",
  "potential_needs": ["至少4条，覆盖双方，包含显性+隐性诉求"],
  "repair_suggestions": ["至少4条，具体到动作/话术，避免空话"],
  "action_tasks": [{"content":"至少3条，含时间锚点或完成标准"}],
  "detailed_report": "一份完整详尽的情感学/心理学分析长文"
}

【detailed_report 的强约束】
必须按以下 8 个小节书写，并保留原样小节标题：
【1. 情绪动态与触发点】
【2. 双方心理需求与防御机制】
【3. 沟通失真链路（谁如何被误读）】
【4. 关系风险评估（短期/中期/长期）】
【5. 修复策略路线图（24小时/7天/30天）】
【6. 高风险表达替换为低伤害表达（给出可直接使用的话术）】
【7. 自我调节与共情练习（双方各至少2条）】
【8. 下次复盘的观察指标（可量化）】

每个小节至少 3 条要点；整段 detailed_report 建议 1200~2200 中文字。
在不确定处明确写“基于现有信息的保守推断”。
输出前请自检字段完整性和最小条目数量，缺一不可。
""".strip()
        user_prompt = (
            "请基于以下转写内容生成中文复盘报告。"
            "先识别冲突事件链，再提炼双方显性表达和隐含情绪需求，最后给出分阶段修复计划。"
            "如果对话证据不足，请在相关结论中写“基于现有信息的保守推断”，不要臆造事实。\n"
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
        return self.settings.env == "test" and self.settings.ai_provider_mode == "mock"

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
        detailed_report = str(payload.get("detailed_report", "")).strip()

        if not potential_needs:
            raise ProviderError("LLM 缺少 potential_needs")
        if not repair_suggestions:
            raise ProviderError("LLM 缺少 repair_suggestions")
        if not action_tasks:
            raise ProviderError("LLM 缺少 action_tasks")
        if not detailed_report:
            raise ProviderError("LLM 缺少 detailed_report")

        return ReportDraft(
            summary=summary[:900],
            potential_needs=potential_needs[:8],
            repair_suggestions=repair_suggestions[:8],
            action_tasks=[ReportDraftTask(content=item.content[:180]) for item in action_tasks[:6]],
            detailed_report=detailed_report[:5200],
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
