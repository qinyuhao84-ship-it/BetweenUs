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


@pytest.fixture(autouse=True)
def clean_database():
    from app.db.session import engine, init_db

    init_db()
    with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            conn.execute(table.delete())
    yield
