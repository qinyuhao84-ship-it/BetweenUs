import hashlib
import json
import logging
import math
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from alibabacloud_dypnsapi20170525 import models as dypns_models
from alibabacloud_dypnsapi20170525.client import Client as AliyunDypnsClient
from alibabacloud_tea_openapi import models as open_api_models
from jose import JWTError, jwt
from sqlmodel import select

from app.core.config import get_settings
from app.db.models import (
    EntitlementModel,
    IAPTransactionModel,
    PaymentOrderModel,
    ProgressModel,
    ReportModel,
    SMSCodeModel,
    SessionModel,
    UserModel,
)
from app.db.session import session_scope
from app.services.apple_services import AppleServiceError, AppleIdentityService

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


@dataclass
class AccountDeletionResult:
    apple_revoked: bool


class AuthService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._apple_identity_service = AppleIdentityService(settings=self._settings)

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
        code = self._generate_sms_code()
        code_id = str(uuid4())
        expires_at = now + timedelta(seconds=self._settings.sms_code_expires_seconds)

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

            code_row = SMSCodeModel(
                code_id=code_id,
                phone=phone,
                purpose="login",
                code_hash=self._hash_sms_code(phone, code),
                created_at=now,
                expires_at=expires_at,
                consumed_at=None,
            )
            db.add(code_row)
            db.commit()

        try:
            self._dispatch_sms(phone=phone, code=code)
        except Exception:
            with session_scope() as db:
                pending_row = db.get(SMSCodeModel, code_id)
                if pending_row is not None and pending_row.consumed_at is None:
                    db.delete(pending_row)
                    db.commit()
            raise
        return SMSCodeSendResult(
            expires_in_seconds=self._settings.sms_code_expires_seconds,
            retry_after_seconds=self._settings.sms_send_interval_seconds,
        )

    def login_with_phone_code(self, phone: str, code: str) -> tuple[str, str, int]:
        user = self._resolve_user_with_phone_code(phone=phone, code=code)
        token, expires_in_minutes = self.issue_access_token(user.user_id)
        return user.user_id, token, expires_in_minutes

    def login_with_apple(
        self,
        identity_token: str,
        authorization_code: str,
        full_name: str = "",
    ) -> tuple[str, str, int]:
        try:
            verified_identity = self.verify_apple_identity_token(identity_token)
            token_exchange = self.exchange_apple_authorization_code(authorization_code)
        except AppleServiceError as exc:
            raise AuthServiceError(str(exc)) from exc

        now = datetime.now(UTC)
        with session_scope() as db:
            user = db.exec(select(UserModel).where(UserModel.apple_subject == verified_identity.subject)).first()
            if user is None:
                user = UserModel(
                    user_id=self._derive_user_id(f"apple:{verified_identity.subject}"),
                    phone="",
                    apple_subject=verified_identity.subject,
                    apple_email=verified_identity.email,
                    apple_refresh_token=token_exchange.refresh_token,
                    nickname=full_name.strip()[:30],
                    created_at=now,
                    last_login_at=now,
                )
            else:
                user.apple_subject = verified_identity.subject
                user.apple_email = verified_identity.email
                user.apple_refresh_token = token_exchange.refresh_token
                if full_name.strip() and not user.nickname.strip():
                    user.nickname = full_name.strip()[:30]
                user.last_login_at = now
            db.add(user)
            db.commit()
            db.refresh(user)

        token, expires_in_minutes = self.issue_access_token(user.user_id)
        return user.user_id, token, expires_in_minutes

    def bind_phone(self, user_id: str, phone: str, code: str) -> UserModel:
        now = datetime.now(UTC)
        normalized_phone = phone.strip()
        self._consume_sms_code(phone=normalized_phone, code=code)

        with session_scope() as db:
            user = db.get(UserModel, user_id)
            if user is None:
                raise KeyError(user_id)

            owner = db.exec(select(UserModel).where(UserModel.phone == normalized_phone)).first()
            if owner is not None and owner.user_id != user_id:
                raise AuthServiceError("该手机号已绑定其他账号")

            user.phone = normalized_phone
            user.last_login_at = now
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

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

    def delete_account(self, user_id: str) -> AccountDeletionResult:
        from app.services.container import audio_storage_service

        with session_scope() as db:
            user = db.get(UserModel, user_id)
            if user is None:
                raise KeyError(user_id)

            apple_revoked = False
            if user.apple_subject:
                if not user.apple_refresh_token:
                    raise AuthServiceError("Apple 账号缺少 refresh_token，无法安全删除")
                try:
                    self.revoke_apple_refresh_token(user.apple_refresh_token)
                except AppleServiceError as exc:
                    raise AuthServiceError(str(exc)) from exc
                apple_revoked = True

            sessions = db.exec(select(SessionModel).where(SessionModel.user_id == user_id)).all()
            for row in sessions:
                if row.audio_file_path:
                    audio_storage_service.cleanup(row.audio_file_path)
                report = db.get(ReportModel, row.session_id)
                if report is not None:
                    db.delete(report)
                progress = db.get(ProgressModel, row.session_id)
                if progress is not None:
                    db.delete(progress)
                db.delete(row)

            for row in db.exec(select(EntitlementModel).where(EntitlementModel.user_id == user_id)).all():
                db.delete(row)
            for row in db.exec(select(IAPTransactionModel).where(IAPTransactionModel.user_id == user_id)).all():
                db.delete(row)
            for row in db.exec(select(PaymentOrderModel).where(PaymentOrderModel.user_id == user_id)).all():
                db.delete(row)
            for row in db.exec(select(SMSCodeModel).where(SMSCodeModel.phone == user.phone)).all():
                db.delete(row)
            db.delete(user)
            db.commit()
            return AccountDeletionResult(apple_revoked=apple_revoked)

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
        if self._settings.sms_provider == "mock":
            logger.info("mock sms sent to %s with code=%s", phone, code)
            return
        try:
            response = self._build_aliyun_sms_client().send_sms_verify_code(
                dypns_models.SendSmsVerifyCodeRequest(
                    phone_number=phone,
                    sign_name=self._settings.sms_aliyun_sign_name,
                    template_code=self._settings.sms_aliyun_template_code,
                    template_param=json.dumps({"code": code}, ensure_ascii=False),
                    valid_time=str(max(1, math.ceil(self._settings.sms_code_expires_seconds / 60))),
                    scheme_name=self._settings.sms_aliyun_scheme_name or None,
                    out_id=f"betweenus-{uuid4().hex[:12]}",
                )
            )
        except Exception as exc:  # noqa: BLE001
            raise AuthServiceError("阿里云短信发送失败，请稍后重试") from exc

        body = getattr(response, "body", None)
        status_code = str(getattr(body, "code", "") or "").upper()
        if status_code != "OK":
            detail = str(getattr(body, "message", "") or "").strip()
            if detail:
                raise AuthServiceError(f"阿里云短信发送失败：{detail}")
            raise AuthServiceError("阿里云短信暂不可用，请稍后重试")

    def _build_aliyun_sms_client(self) -> AliyunDypnsClient:
        config = open_api_models.Config(
            access_key_id=self._settings.sms_aliyun_access_key_id,
            access_key_secret=self._settings.sms_aliyun_access_key_secret,
            endpoint=self._settings.sms_aliyun_endpoint,
        )
        return AliyunDypnsClient(config)

    def verify_access_token(self, token: str) -> str | None:
        try:
            payload = jwt.decode(token, self._settings.jwt_secret_key, algorithms=[self._settings.jwt_algorithm])
        except JWTError:
            return None

        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            return None
        with session_scope() as db:
            user = db.get(UserModel, subject)
            if user is None:
                return None
        return subject

    def verify_apple_identity_token(self, identity_token: str):
        return self._apple_identity_service.verify_identity_token(identity_token)

    def exchange_apple_authorization_code(self, authorization_code: str):
        return self._apple_identity_service.exchange_authorization_code(authorization_code)

    def revoke_apple_refresh_token(self, refresh_token: str) -> None:
        self._apple_identity_service.revoke_refresh_token(refresh_token)

    def _resolve_user_with_phone_code(self, phone: str, code: str) -> UserModel:
        normalized_phone = phone.strip()
        now = datetime.now(UTC)
        self._consume_sms_code(phone=normalized_phone, code=code)

        with session_scope() as db:
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
            return user

    def _consume_sms_code(self, phone: str, code: str) -> None:
        now = datetime.now(UTC)
        normalized_code = code.strip()
        expected_hash = self._hash_sms_code(phone, normalized_code)

        with session_scope() as db:
            code_row = db.exec(
                select(SMSCodeModel)
                .where(
                    SMSCodeModel.phone == phone,
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
            db.commit()
