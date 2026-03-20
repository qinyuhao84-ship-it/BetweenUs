import subprocess

import httpx
import pytest

from app.core.config import Settings
from app.services.ai_providers import ASRService, ProviderError


def _build_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "env": "test",
        "jwt_secret_key": "pytest-secret-key",
        "ai_provider_mode": "real",
        "asr_provider": "volc_recording_bigmodel",
        "asr_volc_app_id": "app-id",
        "asr_volc_access_token": "access-token",
        "asr_volc_resource_id": "volc.seedasr.auc",
        "asr_volc_submit_url": "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit",
        "asr_volc_query_url": "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query",
        "asr_poll_seconds": 0.01,
        "asr_poll_max_attempts": 3,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_volc_asr_requires_public_url_when_upload_disabled(tmp_path):
    audio_file = tmp_path / "sample.wav"
    audio_file.write_bytes(b"fake-audio")
    service = ASRService(settings=_build_settings(asr_volc_upload_provider="none"))

    with pytest.raises(ProviderError, match="公网可访问的音频 URL"):
        service.transcribe(str(audio_file))


def test_volc_asr_submit_and_query_success(tmp_path, monkeypatch):
    audio_file = tmp_path / "sample.wav"
    audio_file.write_bytes(b"fake-audio")
    service = ASRService(settings=_build_settings(asr_volc_upload_provider="catbox"))

    query_count = {"value": 0}

    def fake_post(url: str, *args: object, **kwargs: object) -> httpx.Response:
        if url.endswith("/submit"):
            return httpx.Response(
                200,
                headers={"X-Api-Status-Code": "20000000", "X-Api-Message": "OK"},
                json={},
            )
        if url.endswith("/query"):
            query_count["value"] += 1
            if query_count["value"] == 1:
                return httpx.Response(
                    200,
                    headers={"X-Api-Status-Code": "20000002", "X-Api-Message": "IN_QUEUE"},
                    json={"header": {"code": 20000002, "message": "IN_QUEUE"}},
                )
            return httpx.Response(
                200,
                headers={"X-Api-Status-Code": "20000000", "X-Api-Message": "OK"},
                json={"result": {"text": "这是测试转写结果"}},
            )
        raise AssertionError(f"unexpected url: {url}")

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["curl"],
            returncode=0,
            stdout="https://files.catbox.moe/demo.wav",
            stderr="",
        )

    monkeypatch.setattr("app.services.ai_providers.httpx.post", fake_post)
    monkeypatch.setattr("app.services.ai_providers.subprocess.run", fake_run)
    monkeypatch.setattr("app.services.ai_providers.time.sleep", lambda _seconds: None)

    assert service.transcribe(str(audio_file)) == "这是测试转写结果"
    assert query_count["value"] == 2
