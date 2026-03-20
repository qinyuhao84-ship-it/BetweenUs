from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.core.config import get_settings


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

    def verify_access_token(self, token: str) -> str | None:
        try:
            payload = jwt.decode(token, self._settings.jwt_secret_key, algorithms=[self._settings.jwt_algorithm])
        except JWTError:
            return None

        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            return None
        return subject
