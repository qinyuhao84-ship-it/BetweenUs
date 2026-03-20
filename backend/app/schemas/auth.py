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
