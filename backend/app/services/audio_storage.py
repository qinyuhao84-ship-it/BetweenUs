import re
from pathlib import Path

from fastapi import UploadFile


_ALLOWED_EXTENSIONS = {".m4a", ".mp3", ".wav", ".aac", ".webm"}
_ALLOWED_CONTENT_TYPES = {
    "audio/m4a",
    "audio/x-m4a",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/aac",
    "audio/webm",
    "application/octet-stream",
}
_CHUNK_SIZE = 1024 * 1024


class AudioStorageService:
    def __init__(self, base_dir: str, max_audio_file_bytes: int) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.max_audio_file_bytes = max_audio_file_bytes

    async def save_upload(self, session_id: str, audio_file: UploadFile) -> tuple[str, int]:
        self._validate_session_id(session_id)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(audio_file.filename or "").suffix.lower()
        if suffix not in _ALLOWED_EXTENSIONS:
            raise ValueError("音频格式不支持，仅支持 m4a/mp3/wav/aac/webm")

        content_type = (audio_file.content_type or "").lower().strip()
        if content_type and content_type not in _ALLOWED_CONTENT_TYPES:
            raise ValueError("音频 MIME 类型不支持")

        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        target = session_dir / f"source{suffix}"

        total = 0
        with target.open("wb") as f:
            while True:
                chunk = await audio_file.read(_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > self.max_audio_file_bytes:
                    f.close()
                    target.unlink(missing_ok=True)
                    raise ValueError("音频文件过大，请控制在 25MB 以内")
                f.write(chunk)

        await audio_file.close()
        if total == 0:
            target.unlink(missing_ok=True)
            raise ValueError("上传失败，音频为空")
        return str(target), total

    def cleanup(self, audio_path: str) -> None:
        if not audio_path:
            return
        target = Path(audio_path).resolve()
        try:
            target.relative_to(self.base_dir)
        except ValueError:
            return
        if not target.exists():
            return
        try:
            target.unlink(missing_ok=True)
            parent = target.parent
            if parent != self.base_dir and parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        except OSError:
            # 清理失败不应影响主流程。
            return

    @staticmethod
    def _validate_session_id(session_id: str) -> None:
        if not re.fullmatch(r"[a-zA-Z0-9\-]+", session_id):
            raise ValueError("会话 ID 非法")
