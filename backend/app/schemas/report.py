from pydantic import BaseModel


class ActionTask(BaseModel):
    task_id: str
    content: str
    done: bool = False


class ReportDraftTask(BaseModel):
    content: str


class ReportDraft(BaseModel):
    summary: str
    potential_needs: list[str]
    repair_suggestions: list[str]
    action_tasks: list[ReportDraftTask]
    detailed_report: str


class ReportResponse(BaseModel):
    session_id: str
    summary: str
    transcript_excerpt: str = ""
    potential_needs: list[str]
    repair_suggestions: list[str]
    action_tasks: list[ActionTask]
    detailed_report: str = ""
