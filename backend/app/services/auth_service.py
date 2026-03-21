import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from jose import JWTError, jwt
from sqlmodel import select

from app.core.config import get_settings
from app.db.models import SMSCodeModel, UserModel
from app.db.session import session_scope

logger = logging.getLogger(__name__)


class AuthServiceError(RuntimeError):
    pass


class SMSCodeCooldownError(AuthServiceError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("验证码发送过于频繁，请稍后再试")
        self.retry_after_seconds = retry_after_seconds


class SMSCodeInvalidError(AuthServiceError):
    pass


@dataclass
class SMSCodeSendResult:
    expires_in_seconds: int
    retry_after_seconds: int
    dev_code: str | None


class AuthService:
    def __init__(self) -> None:
        self._settings = get_settings()

    def issue_access_token(self, user_id: str) -> tuple[str, int]:
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=self._settings.access_token_expire_minutes)
        payload = {
            "sub": user_id,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(payload, self._settings.jwt_secret_key, algorithm=self._settings.jwt_algorithm)
        return token, self._settings.access_token_expire_minutes

    def send_login_code(self, phone: str) -> SMSCodeSendResult:
        now = datetime.now(UTC)
        phone = phone.strip()

        with session_scope() as db:
            latest = db.exec(
                select(SMSCodeModel)
                .where(
                    SMSCodeModel.phone == phone,
                    SMSCodeModel.purpose == "login",
                )
                .order_by(SMSCodeModel.created_at.desc())
            ).first()

            if latest is not None:
                latest_created_at = self._to_utc(latest.created_at)
                elapsed = int((now - latest_created_at).total_seconds())
                if elapsed < self._settings.sms_send_interval_seconds:
                    raise SMSCodeCooldownError(self._settings.sms_send_interval_seconds - elapsed)

            code = self._generate_sms_code()
            code_row = SMSCodeModel(
                code_id=str(uuid4()),
                phone=phone,
                purpose="login",
                code_hash=self._hash_sms_code(phone, code),
                created_at=now,
                expires_at=now + timedelta(seconds=self._settings.sms_code_expires_seconds),
                consumed_at=None,
            )
            db.add(code_row)
            db.commit()

        self._dispatch_sms(phone=phone, code=code)
        dev_code = code if self._settings.env in {"dev", "test"} else None
        return SMSCodeSendResult(
            expires_in_seconds=self._settings.sms_code_expires_seconds,
            retry_after_seconds=self._settings.sms_send_interval_seconds,
            dev_code=dev_code,
        )

    def login_with_phone_code(self, phone: str, code: str) -> tuple[str, str, int]:
        now = datetime.now(UTC)
        normalized_phone = phone.strip()
        normalized_code = code.strip()
        expected_hash = self._hash_sms_code(normalized_phone, normalized_code)

        with session_scope() as db:
            code_row = db.exec(
                select(SMSCodeModel)
                .where(
                    SMSCodeModel.phone == normalized_phone,
                    SMSCodeModel.purpose == "login",
                    SMSCodeModel.consumed_at.is_(None),
                )
                .order_by(SMSCodeModel.created_at.desc())
            ).first()
            if code_row is None:
                raise SMSCodeInvalidError("验证码不存在，请先获取验证码")
            expires_at = self._to_utc(code_row.expires_at)
            if expires_at < now:
                raise SMSCodeInvalidError("验证码已过期，请重新获取")
            if code_row.code_hash != expected_hash:
                raise SMSCodeInvalidError("验证码错误，请重新输入")

            code_row.consumed_at = now
            db.add(code_row)

            user = db.exec(select(UserModel).where(UserModel.phone == normalized_phone)).first()
            if user is None:
                user = UserModel(
                    user_id=self._derive_user_id(normalized_phone),
                    phone=normalized_phone,
                    nickname="",
                    created_at=now,
                    last_login_at=now,
                )
            else:
                user.last_login_at = now
            db.add(user)
            db.commit()
            db.refresh(user)

        token, expires_in_minutes = self.issue_access_token(user.user_id)
        return user.user_id, token, expires_in_minutes

    def get_profile(self, user_id: str) -> UserModel:
        with session_scope() as db:
            user = db.get(UserModel, user_id)
            if user is None:
                raise KeyError(user_id)
            return user

    def update_profile_nickname(self, user_id: str, nickname: str) -> UserModel:
        now = datetime.now(UTC)
        with session_scope() as db:
            user = db.get(UserModel, user_id)
            if user is None:
                raise KeyError(user_id)
            user.nickname = nickname.strip()
            user.last_login_at = now
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    @staticmethod
    def mask_phone(phone: str) -> str:
        if len(phone) != 11:
            return phone
        return f"{phone[:3]}****{phone[-4:]}"

    @staticmethod
    def _derive_user_id(seed: str) -> str:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
        return f"u_{digest}"

    @staticmethod
    def _generate_sms_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    def _hash_sms_code(self, phone: str, code: str) -> str:
        raw = f"{phone}:{code}:{self._settings.jwt_secret_key}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _to_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _dispatch_sms(self, phone: str, code: str) -> None:
        message = self._settings.sms_template.format(code=code)
        if self._settings.sms_provider == "mock":
            logger.info("mock sms sent to %s with code=%s", phone, code)
            return

        headers: dict[str, str] = {}
        if self._settings.sms_http_auth_token:
            headers["Authorization"] = f"Bearer {self._settings.sms_http_auth_token}"

        payload = {"phone": phone, "message": message, "code": code}
        try:
            response = httpx.post(
                self._settings.sms_http_endpoint,
                json=payload,
                headers=headers,
                timeout=self._settings.provider_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise AuthServiceError("短信网关请求失败，请稍后重试") from exc

        if response.status_code >= 400:
            raise AuthServiceError("短信网关暂不可用，请稍后重试")

    def verify_access_token(self, token: str) -> str | None:
        try:
            payload = jwt.decode(token, self._settings.jwt_secret_key, algorithms=[self._settings.jwt_algorithm])
        except JWTError:
            return None

        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            return None
        return subject
