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


class ReportResponse(BaseModel):
    session_id: str
    summary: str
    potential_needs: list[str]
    repair_suggestions: list[str]
    action_tasks: list[ActionTask]
