from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


def _build_engine():
    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


engine = _build_engine()


def init_db() -> None:
    # Import models before create_all so metadata can discover table definitions.
    from app.db import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _run_compat_migrations()


def _run_compat_migrations() -> None:
    with engine.begin() as conn:
        inspector = inspect(conn)
        if "sessions" not in inspector.get_table_names():
            return

        existing_columns = {col["name"] for col in inspector.get_columns("sessions")}
        migration_sql: list[str] = []
        if "audio_file_path" not in existing_columns:
            migration_sql.append("ALTER TABLE sessions ADD COLUMN audio_file_path TEXT NOT NULL DEFAULT ''")
        if "transcript_text" not in existing_columns:
            migration_sql.append("ALTER TABLE sessions ADD COLUMN transcript_text TEXT NOT NULL DEFAULT ''")
        if "failure_reason" not in existing_columns:
            migration_sql.append("ALTER TABLE sessions ADD COLUMN failure_reason TEXT NOT NULL DEFAULT ''")

        for sql in migration_sql:
            conn.execute(text(sql))


@contextmanager
def session_scope() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
