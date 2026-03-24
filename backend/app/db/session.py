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
        table_names = inspector.get_table_names()
        if "sessions" in table_names:
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

        if "reports" in table_names:
            report_columns = {col["name"] for col in inspector.get_columns("reports")}
            if "detailed_report_text" not in report_columns:
                conn.execute(text("ALTER TABLE reports ADD COLUMN detailed_report_text TEXT NOT NULL DEFAULT ''"))

        if "users" in table_names:
            user_columns = {col["name"] for col in inspector.get_columns("users")}
            if "apple_subject" not in user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN apple_subject TEXT NOT NULL DEFAULT ''"))
            if "apple_email" not in user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN apple_email TEXT NOT NULL DEFAULT ''"))
            if "apple_refresh_token" not in user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN apple_refresh_token TEXT NOT NULL DEFAULT ''"))

        if "iap_transactions" in table_names:
            iap_columns = {col["name"] for col in inspector.get_columns("iap_transactions")}
            migration_sql = []
            if "original_transaction_id" not in iap_columns:
                migration_sql.append(
                    "ALTER TABLE iap_transactions ADD COLUMN original_transaction_id TEXT NOT NULL DEFAULT ''"
                )
            if "signed_transaction_info" not in iap_columns:
                migration_sql.append(
                    "ALTER TABLE iap_transactions ADD COLUMN signed_transaction_info TEXT NOT NULL DEFAULT ''"
                )
            if "environment" not in iap_columns:
                migration_sql.append("ALTER TABLE iap_transactions ADD COLUMN environment TEXT NOT NULL DEFAULT ''")
            if "purchase_date_ms" not in iap_columns:
                migration_sql.append("ALTER TABLE iap_transactions ADD COLUMN purchase_date_ms INTEGER NOT NULL DEFAULT 0")
            if "signed_date_ms" not in iap_columns:
                migration_sql.append("ALTER TABLE iap_transactions ADD COLUMN signed_date_ms INTEGER NOT NULL DEFAULT 0")
            if "revocation_date_ms" not in iap_columns:
                migration_sql.append(
                    "ALTER TABLE iap_transactions ADD COLUMN revocation_date_ms INTEGER NOT NULL DEFAULT 0"
                )
            if "revocation_reason" not in iap_columns:
                migration_sql.append("ALTER TABLE iap_transactions ADD COLUMN revocation_reason INTEGER NOT NULL DEFAULT -1")
            if "revoked" not in iap_columns:
                migration_sql.append("ALTER TABLE iap_transactions ADD COLUMN revoked BOOLEAN NOT NULL DEFAULT 0")
            for sql in migration_sql:
                conn.execute(text(sql))


@contextmanager
def session_scope() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
