import hashlib

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user_id
from app.schemas.auth import (
    AppleLoginRequest,
    AuthResponse,
    PhoneBindRequest,
    PhoneLoginRequest,
    SendSMSCodeRequest,
    SendSMSCodeResponse,
    UpdateProfileRequest,
    UserProfileResponse,
)
from app.services.auth_service import AuthServiceError, SMSCodeCooldownError, SMSCodeInvalidError
from app.services.container import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _derive_user_id(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"u_{digest}"


def _to_profile_response(user_id: str) -> UserProfileResponse:
    try:
        profile = auth_service.get_profile(user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="用户不存在") from exc
    return UserProfileResponse(
        user_id=profile.user_id,
        phone=profile.phone,
        phone_masked=auth_service.mask_phone(profile.phone),
        nickname=profile.nickname,
        created_at=profile.created_at,
        last_login_at=profile.last_login_at,
    )


@router.post("/apple-login", response_model=AuthResponse)
def apple_login(payload: AppleLoginRequest) -> AuthResponse:
    user_id = _derive_user_id(payload.apple_identity_token)
    token, expires_in_minutes = auth_service.issue_access_token(user_id)
    return AuthResponse(user_id=user_id, access_token=token, expires_in_minutes=expires_in_minutes)


@router.post("/phone-bind", response_model=AuthResponse)
def bind_phone(payload: PhoneBindRequest) -> AuthResponse:
    try:
        user_id, token, expires_in_minutes = auth_service.login_with_phone_code(payload.phone, payload.code)
    except SMSCodeInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuthServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AuthResponse(
        user_id=user_id,
        access_token=token,
        expires_in_minutes=expires_in_minutes,
        phone=payload.phone,
        phone_masked=auth_service.mask_phone(payload.phone),
    )


@router.post("/sms/send", response_model=SendSMSCodeResponse)
def send_sms_code(payload: SendSMSCodeRequest) -> SendSMSCodeResponse:
    try:
        result = auth_service.send_login_code(payload.phone)
    except SMSCodeCooldownError as exc:
        raise HTTPException(status_code=429, detail=f"请 {exc.retry_after_seconds} 秒后再获取验证码") from exc
    except AuthServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return SendSMSCodeResponse(
        sent=True,
        expires_in_seconds=result.expires_in_seconds,
        retry_after_seconds=result.retry_after_seconds,
        dev_code=result.dev_code,
    )


@router.post("/sms/login", response_model=AuthResponse)
def login_with_sms(payload: PhoneLoginRequest) -> AuthResponse:
    try:
        user_id, token, expires_in_minutes = auth_service.login_with_phone_code(payload.phone, payload.code)
    except SMSCodeInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuthServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AuthResponse(
        user_id=user_id,
        access_token=token,
        expires_in_minutes=expires_in_minutes,
        phone=payload.phone,
        phone_masked=auth_service.mask_phone(payload.phone),
    )


@router.get("/me", response_model=UserProfileResponse)
def me(user_id: str = Depends(get_current_user_id)) -> UserProfileResponse:
    return _to_profile_response(user_id)


@router.patch("/me", response_model=UserProfileResponse)
def update_me(payload: UpdateProfileRequest, user_id: str = Depends(get_current_user_id)) -> UserProfileResponse:
    try:
        auth_service.update_profile_nickname(user_id=user_id, nickname=payload.nickname)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="用户不存在") from exc
    return _to_profile_response(user_id)
