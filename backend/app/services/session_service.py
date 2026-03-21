import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlmodel import select

from app.db.models import ReportModel, SessionModel
from app.db.session import session_scope
from app.schemas.report import ActionTask, ReportResponse


@dataclass
class SessionRecord:
    session_id: str
    user_id: str
    title: str
    status: str
    created_at: datetime
    duration_minutes: int = 0
    audio_file_path: str = ""
    transcript_text: str = ""
    failure_reason: str = ""


class SessionService:
    def create_session(self, user_id: str, title: str) -> SessionRecord:
        with session_scope() as db:
            row = SessionModel(
                session_id=str(uuid4()),
                user_id=user_id,
                title=title,
                status="recording",
                created_at=datetime.now(UTC),
                audio_file_path="",
                transcript_text="",
                failure_reason="",
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_record(row)

    def attach_audio(self, session_id: str, audio_file_path: str) -> SessionRecord:
        with session_scope() as db:
            row = db.get(SessionModel, session_id)
            if row is None:
                raise KeyError(session_id)
            row.audio_file_path = audio_file_path
            row.failure_reason = ""
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_record(row)

    def finish(self, session_id: str, duration_minutes: int) -> SessionRecord:
        with session_scope() as db:
            row = db.get(SessionModel, session_id)
            if row is None:
                raise KeyError(session_id)
            row.duration_minutes = duration_minutes
            row.status = "processing"
            row.failure_reason = ""
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_record(row)

    def complete(self, session_id: str, transcript: str, report: ReportResponse) -> SessionRecord:
        with session_scope() as db:
            session_row = db.get(SessionModel, session_id)
            if session_row is None:
                raise KeyError(session_id)

            session_row.status = "completed"
            session_row.transcript_text = transcript
            session_row.failure_reason = ""
            report_row = db.get(ReportModel, session_id)
            if report_row is None:
                report_row = ReportModel(
                    session_id=session_id,
                    summary=report.summary,
                    potential_needs_json=json.dumps(report.potential_needs, ensure_ascii=False),
                    repair_suggestions_json=json.dumps(report.repair_suggestions, ensure_ascii=False),
                    action_tasks_json=json.dumps([task.model_dump() for task in report.action_tasks], ensure_ascii=False),
                    created_at=datetime.now(UTC),
                )
            else:
                report_row.summary = report.summary
                report_row.potential_needs_json = json.dumps(report.potential_needs, ensure_ascii=False)
                report_row.repair_suggestions_json = json.dumps(report.repair_suggestions, ensure_ascii=False)
                report_row.action_tasks_json = json.dumps(
                    [task.model_dump() for task in report.action_tasks],
                    ensure_ascii=False,
                )

            db.add(session_row)
            db.add(report_row)
            db.commit()
            db.refresh(session_row)
            return self._to_record(session_row)

    def fail(self, session_id: str, reason: str) -> SessionRecord:
        with session_scope() as db:
            row = db.get(SessionModel, session_id)
            if row is None:
                raise KeyError(session_id)
            row.status = "failed"
            row.failure_reason = reason.strip()[:300]
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_record(row)

    def get_session(self, session_id: str) -> SessionRecord:
        with session_scope() as db:
            row = db.get(SessionModel, session_id)
            if row is None:
                raise KeyError(session_id)
            return self._to_record(row)

    def list_by_user(self, user_id: str) -> list[SessionRecord]:
        with session_scope() as db:
            rows = db.exec(select(SessionModel).where(SessionModel.user_id == user_id)).all()
            return [self._to_record(row) for row in rows]

    def get_report(self, session_id: str) -> ReportResponse:
        with session_scope() as db:
            row = db.get(ReportModel, session_id)
            if row is None:
                raise KeyError(session_id)
            session_row = db.get(SessionModel, session_id)
            transcript_excerpt = ""
            if session_row is not None and session_row.transcript_text:
                transcript_excerpt = session_row.transcript_text.strip()
                if len(transcript_excerpt) > 280:
                    transcript_excerpt = transcript_excerpt[:280] + "..."
            action_tasks = [ActionTask.model_validate(item) for item in json.loads(row.action_tasks_json)]
            return ReportResponse(
                session_id=row.session_id,
                summary=row.summary,
                transcript_excerpt=transcript_excerpt,
                potential_needs=list(json.loads(row.potential_needs_json)),
                repair_suggestions=list(json.loads(row.repair_suggestions_json)),
                action_tasks=action_tasks,
            )

    @staticmethod
    def _to_record(row: SessionModel) -> SessionRecord:
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return SessionRecord(
            session_id=row.session_id,
            user_id=row.user_id,
            title=row.title,
            status=row.status,
            created_at=created_at,
            duration_minutes=row.duration_minutes,
            audio_file_path=row.audio_file_path,
            transcript_text=row.transcript_text,
            failure_reason=row.failure_reason,
        )
