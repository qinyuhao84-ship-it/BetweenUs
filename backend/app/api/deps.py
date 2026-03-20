from typing import Annotated

from fastapi import Header, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.services.container import auth_service

UserIdHeader = Annotated[str | None, Header(alias="X-User-Id")]
CredentialsHeader = Annotated[HTTPAuthorizationCredentials | None, Security(HTTPBearer(auto_error=False))]


def get_current_user_id(
    credentials: CredentialsHeader = None,
    x_user_id: UserIdHeader = None,
) -> str:
    if credentials and credentials.credentials:
        user_id = auth_service.verify_access_token(credentials.credentials)
        if user_id:
            return user_id
        raise HTTPException(status_code=401, detail="访问令牌无效或已过期")

    settings = get_settings()
    if settings.allow_insecure_header_auth and x_user_id:
        return x_user_id

    raise HTTPException(status_code=401, detail="缺少 Bearer 访问令牌")
