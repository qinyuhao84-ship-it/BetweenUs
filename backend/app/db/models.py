from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class SessionModel(SQLModel, table=True):
    __tablename__ = "sessions"

    session_id: str = Field(primary_key=True, index=True)
    user_id: str = Field(index=True)
    title: str
    status: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    duration_minutes: int = Field(default=0)
    audio_file_path: str = Field(default="")
    transcript_text: str = Field(default="")
    failure_reason: str = Field(default="")


class ReportModel(SQLModel, table=True):
    __tablename__ = "reports"

    session_id: str = Field(primary_key=True, foreign_key="sessions.session_id")
    summary: str
    potential_needs_json: str
    repair_suggestions_json: str
    action_tasks_json: str
    detailed_report_text: str = Field(default="")
    created_at: datetime = Field(default_factory=utcnow)


class EntitlementModel(SQLModel, table=True):
    __tablename__ = "entitlements"

    user_id: str = Field(primary_key=True)
    subscription_units_left: int
    payg_units_left: int
    updated_at: datetime = Field(default_factory=utcnow)


class IAPTransactionModel(SQLModel, table=True):
    __tablename__ = "iap_transactions"

    transaction_id: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    original_transaction_id: str = Field(default="", index=True)
    product_id: str = Field(default="", index=True)
    signed_transaction_info: str = Field(default="")
    units: int = Field(default=0)
    environment: str = Field(default="")
    purchase_date_ms: int = Field(default=0)
    signed_date_ms: int = Field(default=0)
    revocation_date_ms: int = Field(default=0)
    revocation_reason: int = Field(default=-1)
    revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)


class PaymentOrderModel(SQLModel, table=True):
    __tablename__ = "payment_orders"

    order_no: str = Field(primary_key=True, index=True)
    user_id: str = Field(index=True)
    package_id: str = Field(index=True)
    channel: str = Field(index=True)
    units: int = Field(default=0)
    amount_cny: int = Field(default=0)
    status: str = Field(default="pending", index=True)
    provider_order_id: str = Field(default="")
    payment_payload: str = Field(default="")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ProgressModel(SQLModel, table=True):
    __tablename__ = "progress_points"

    session_id: str = Field(primary_key=True, foreign_key="sessions.session_id")
    stage: str
    percent: int
    updated_at: datetime = Field(default_factory=utcnow)


class UserModel(SQLModel, table=True):
    __tablename__ = "users"

    user_id: str = Field(primary_key=True, index=True)
    phone: str = Field(default="", index=True)
    apple_subject: str = Field(default="", index=True)
    apple_email: str = Field(default="")
    apple_refresh_token: str = Field(default="")
    nickname: str = Field(default="")
    created_at: datetime = Field(default_factory=utcnow)
    last_login_at: datetime = Field(default_factory=utcnow)


class SMSCodeModel(SQLModel, table=True):
    __tablename__ = "sms_codes"

    code_id: str = Field(primary_key=True, index=True)
    phone: str = Field(index=True)
    purpose: str = Field(index=True, default="login")
    code_hash: str
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    consumed_at: datetime | None = Field(default=None)
