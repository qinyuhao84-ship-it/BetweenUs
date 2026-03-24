from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from jose import JWTError, jwt

from app.core.config import Settings


class AppleServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class VerifiedAppleIdentity:
    subject: str
    email: str
    email_verified: bool


@dataclass(frozen=True)
class AppleTokenExchange:
    refresh_token: str


@dataclass(frozen=True)
class VerifiedAppStoreTransaction:
    transaction_id: str
    original_transaction_id: str
    product_id: str
    signed_transaction_info: str
    environment: str
    purchase_date_ms: int
    signed_date_ms: int
    revocation_date_ms: int | None
    revocation_reason: int | None


@dataclass(frozen=True)
class DecodedAppStoreNotification:
    notification_type: str
    subtype: str
    signed_transaction_info: str


class AppleIdentityService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def verify_identity_token(self, identity_token: str) -> VerifiedAppleIdentity:
        token = identity_token.strip()
        if not token:
            raise AppleServiceError("Apple 身份令牌为空")

        try:
            headers = jwt.get_unverified_header(token)
            key_id = str(headers.get("kid", "")).strip()
        except JWTError as exc:
            raise AppleServiceError("Apple 身份令牌格式无效") from exc

        if not key_id:
            raise AppleServiceError("Apple 身份令牌缺少 kid")

        try:
            response = httpx.get(self.settings.apple_jwks_url, timeout=self.settings.provider_timeout_seconds)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AppleServiceError("获取 Apple 公钥失败，请稍后重试") from exc

        keys = body.get("keys", []) if isinstance(body, dict) else []
        matching_key = next((item for item in keys if isinstance(item, dict) and item.get("kid") == key_id), None)
        if matching_key is None:
            raise AppleServiceError("Apple 公钥未匹配到当前令牌")

        audience = self.settings.apple_sign_in_audience or self.settings.apple_client_id
        try:
            payload = jwt.decode(
                token,
                matching_key,
                algorithms=["RS256"],
                audience=audience,
                issuer="https://appleid.apple.com",
            )
        except JWTError as exc:
            raise AppleServiceError("Apple 身份令牌校验失败") from exc

        subject = str(payload.get("sub", "")).strip()
        if not subject:
            raise AppleServiceError("Apple 身份令牌缺少用户标识")

        email = str(payload.get("email", "")).strip()
        raw_email_verified = payload.get("email_verified", False)
        email_verified = raw_email_verified in {True, "true", "True", 1, "1"}
        return VerifiedAppleIdentity(subject=subject, email=email, email_verified=email_verified)

    def exchange_authorization_code(self, authorization_code: str) -> AppleTokenExchange:
        code = authorization_code.strip()
        if not code:
            raise AppleServiceError("Apple 授权码为空")

        client_secret = self._build_client_secret()
        payload = {
            "client_id": self.settings.apple_client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        }
        try:
            response = httpx.post(
                self.settings.apple_token_url,
                data=payload,
                timeout=self.settings.provider_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AppleServiceError("Apple 授权码交换失败") from exc

        refresh_token = str(body.get("refresh_token", "")).strip() if isinstance(body, dict) else ""
        if not refresh_token:
            raise AppleServiceError("Apple 未返回 refresh_token，无法完成正式登录")
        return AppleTokenExchange(refresh_token=refresh_token)

    def revoke_refresh_token(self, refresh_token: str) -> None:
        normalized = refresh_token.strip()
        if not normalized:
            raise AppleServiceError("Apple refresh_token 为空，无法撤销")

        client_secret = self._build_client_secret()
        payload = {
            "client_id": self.settings.apple_client_id,
            "client_secret": client_secret,
            "token": normalized,
            "token_type_hint": "refresh_token",
        }
        try:
            response = httpx.post(
                self.settings.apple_revoke_url,
                data=payload,
                timeout=self.settings.provider_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AppleServiceError("撤销 Apple 登录失败") from exc

    def _build_client_secret(self) -> str:
        now = int(time.time())
        payload = {
            "iss": self.settings.apple_team_id,
            "iat": now,
            "exp": now + 60 * 60 * 24 * 180,
            "aud": "https://appleid.apple.com",
            "sub": self.settings.apple_client_id,
        }
        try:
            return jwt.encode(
                payload,
                self.settings.apple_private_key.replace("\\n", "\n"),
                algorithm="ES256",
                headers={"kid": self.settings.apple_key_id},
            )
        except JWTError as exc:
            raise AppleServiceError("生成 Apple client secret 失败") from exc


class AppStoreVerificationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._verifier: Any | None = None

    def verify_signed_transaction(self, signed_transaction_info: str) -> VerifiedAppStoreTransaction:
        payload = self._signed_data_verifier.verify_and_decode_signed_transaction(signed_transaction_info.strip())
        return VerifiedAppStoreTransaction(
            transaction_id=str(payload.transactionId),
            original_transaction_id=str(payload.originalTransactionId),
            product_id=str(payload.productId),
            signed_transaction_info=signed_transaction_info.strip(),
            environment=str(payload.environment),
            purchase_date_ms=int(payload.purchaseDate),
            signed_date_ms=int(payload.signedDate),
            revocation_date_ms=int(payload.revocationDate) if payload.revocationDate is not None else None,
            revocation_reason=int(payload.revocationReason) if payload.revocationReason is not None else None,
        )

    def verify_notification(self, signed_payload: str) -> DecodedAppStoreNotification:
        payload = self._signed_data_verifier.verify_and_decode_notification(signed_payload.strip())
        signed_transaction_info = ""
        if payload.data and payload.data.signedTransactionInfo:
            signed_transaction_info = str(payload.data.signedTransactionInfo).strip()
        if not signed_transaction_info:
            raise AppleServiceError("App Store 通知未包含 signedTransactionInfo")
        return DecodedAppStoreNotification(
            notification_type=str(payload.notificationType or "").strip(),
            subtype=str(payload.subtype or "").strip(),
            signed_transaction_info=signed_transaction_info,
        )

    @property
    def _signed_data_verifier(self):
        if self._verifier is not None:
            return self._verifier

        from appstoreserverlibrary.models.Environment import Environment
        from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier

        environment_map = {
            "local_testing": Environment.LOCAL_TESTING,
            "sandbox": Environment.SANDBOX,
            "production": Environment.PRODUCTION,
        }
        selected_environment = environment_map.get(self.settings.apple_iap_environment, Environment.PRODUCTION)
        root_certificates = self._load_root_certificates()
        self._verifier = SignedDataVerifier(
            root_certificates=root_certificates,
            enable_online_checks=selected_environment not in {Environment.LOCAL_TESTING},
            environment=selected_environment,
            bundle_id=self.settings.apple_iap_bundle_id or self.settings.apple_client_id,
            app_apple_id=self.settings.apple_iap_app_apple_id,
        )
        return self._verifier

    def _load_root_certificates(self) -> list[bytes]:
        if self.settings.apple_iap_environment == "local_testing":
            return [b"local-testing-root"]

        paths = [item.strip() for item in self.settings.apple_iap_root_ca_paths.split(",") if item.strip()]
        if not paths:
            raise AppleServiceError("Apple Root CA 证书未配置")

        certificates: list[bytes] = []
        for raw_path in paths:
            path = Path(raw_path).expanduser()
            certificates.append(path.read_bytes())
        return certificates
