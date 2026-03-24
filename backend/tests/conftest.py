import os
from pathlib import Path

import pytest
from sqlmodel import SQLModel

TEST_DB_PATH = Path(__file__).resolve().parent / ".pytest_betweenus.db"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ.setdefault("ENV", "test")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")
os.environ.setdefault("JWT_SECRET_KEY", "pytest-secret-key")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")
os.environ.setdefault("AI_PROVIDER_MODE", "mock")
os.environ.setdefault("SMS_PROVIDER", "mock")
os.environ["ASR_VOLC_UPLOAD_PROVIDER"] = "none"
os.environ.setdefault("APPLE_CLIENT_ID", "com.betweenus.app")
os.environ.setdefault("APPLE_SIGN_IN_AUDIENCE", "com.betweenus.app")
os.environ.setdefault("APPLE_TEAM_ID", "pytest-team")
os.environ.setdefault("APPLE_KEY_ID", "pytest-key")
os.environ.setdefault("APPLE_PRIVATE_KEY", "-----BEGIN PRIVATE KEY-----\\npytest\\n-----END PRIVATE KEY-----")
os.environ.setdefault("APPLE_IAP_BUNDLE_ID", "com.betweenus.app")
os.environ.setdefault("APPLE_IAP_ENVIRONMENT", "local_testing")


@pytest.fixture(autouse=True)
def clean_database():
    from app.db.session import engine, init_db

    init_db()
    with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            conn.execute(table.delete())
    yield


@pytest.fixture(autouse=True)
def stable_sms_code(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.services.auth_service.AuthService._generate_sms_code",
        staticmethod(lambda: "123456"),
    )
