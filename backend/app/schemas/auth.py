from datetime import datetime

from pydantic import BaseModel, Field


class AppleLoginRequest(BaseModel):
    apple_identity_token: str = Field(min_length=8)


class PhoneBindRequest(BaseModel):
    phone: str = Field(pattern=r"^1\d{10}$")
    code: str = Field(min_length=4, max_length=6)


class AuthResponse(BaseModel):
    user_id: str
    access_token: str
    token_type: str = "Bearer"
    expires_in_minutes: int
    phone: str | None = None
    phone_masked: str | None = None


class SendSMSCodeRequest(BaseModel):
    phone: str = Field(pattern=r"^1\d{10}$")


class SendSMSCodeResponse(BaseModel):
    sent: bool
    expires_in_seconds: int
    retry_after_seconds: int
    dev_code: str | None = None


class PhoneLoginRequest(BaseModel):
    phone: str = Field(pattern=r"^1\d{10}$")
    code: str = Field(min_length=4, max_length=6)


class UserProfileResponse(BaseModel):
    user_id: str
    phone: str
    phone_masked: str
    nickname: str
    created_at: datetime
    last_login_at: datetime


class UpdateProfileRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=30)
