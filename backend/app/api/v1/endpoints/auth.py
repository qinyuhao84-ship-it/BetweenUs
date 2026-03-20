import hashlib

from fastapi import APIRouter
from fastapi import HTTPException

from app.core.config import get_settings
from app.schemas.auth import AppleLoginRequest, AuthResponse, PhoneBindRequest
from app.services.container import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _derive_user_id(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"u_{digest}"


@router.post("/apple-login", response_model=AuthResponse)
def apple_login(payload: AppleLoginRequest) -> AuthResponse:
    user_id = _derive_user_id(payload.apple_identity_token)
    token, expires_in_minutes = auth_service.issue_access_token(user_id)
    return AuthResponse(user_id=user_id, access_token=token, expires_in_minutes=expires_in_minutes)


@router.post("/phone-bind", response_model=AuthResponse)
def bind_phone(payload: PhoneBindRequest) -> AuthResponse:
    if get_settings().env not in {"dev", "test"}:
        raise HTTPException(status_code=501, detail="手机号绑定暂未接入正式短信验证")
    user_id = _derive_user_id(payload.phone)
    token, expires_in_minutes = auth_service.issue_access_token(user_id)
    return AuthResponse(user_id=user_id, access_token=token, expires_in_minutes=expires_in_minutes)
