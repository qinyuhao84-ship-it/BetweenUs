from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.models import ProgressModel
from app.db.session import session_scope


_STAGE_ORDER = {
    "queued": 0,
    "transcribing": 1,
    "analyzing": 2,
    "rendering": 3,
    "completed": 4,
    "failed": 5,
}


@dataclass
class ProgressPoint:
    stage: str
    percent: int
    updated_at: datetime


class ProgressService:
    def start(self, session_id: str) -> ProgressPoint:
        with session_scope() as db:
            row = db.get(ProgressModel, session_id)
            if row is None:
                row = ProgressModel(session_id=session_id, stage="queued", percent=5, updated_at=datetime.now(UTC))
            else:
                row.stage = "queued"
                row.percent = max(row.percent, 5)
                row.updated_at = datetime.now(UTC)
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_point(row)

    def advance(self, session_id: str, stage: str, percent: int) -> ProgressPoint:
        with session_scope() as db:
            row = db.get(ProgressModel, session_id)
            if row is None:
                row = ProgressModel(session_id=session_id, stage="queued", percent=5, updated_at=datetime.now(UTC))

            safe_stage = stage
            safe_percent = min(max(percent, 0), 99)
            if _STAGE_ORDER.get(safe_stage, -1) < _STAGE_ORDER.get(row.stage, -1):
                safe_stage = row.stage
            if safe_percent < row.percent:
                safe_percent = row.percent

            row.stage = safe_stage
            row.percent = safe_percent
            row.updated_at = datetime.now(UTC)
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_point(row)

    def complete(self, session_id: str) -> ProgressPoint:
        with session_scope() as db:
            row = db.get(ProgressModel, session_id)
            if row is None:
                row = ProgressModel(session_id=session_id, stage="completed", percent=100, updated_at=datetime.now(UTC))
            else:
                row.stage = "completed"
                row.percent = 100
                row.updated_at = datetime.now(UTC)
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_point(row)

    def fail(self, session_id: str) -> ProgressPoint:
        with session_scope() as db:
            row = db.get(ProgressModel, session_id)
            if row is None:
                row = ProgressModel(session_id=session_id, stage="failed", percent=100, updated_at=datetime.now(UTC))
            else:
                row.stage = "failed"
                row.percent = max(row.percent, 100)
                row.updated_at = datetime.now(UTC)
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_point(row)

    def get(self, session_id: str) -> ProgressPoint:
        with session_scope() as db:
            row = db.get(ProgressModel, session_id)
            if row is None:
                return ProgressPoint(stage="queued", percent=0, updated_at=datetime.now(UTC))
            return self._to_point(row)

    @staticmethod
    def _to_point(row: ProgressModel) -> ProgressPoint:
        updated_at = row.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        return ProgressPoint(stage=row.stage, percent=row.percent, updated_at=updated_at)
