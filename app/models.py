from pydantic import BaseModel
from enum import Enum


class StepStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskStep(BaseModel):
    step_id: int
    action: str
    params: dict
    depends_on: list[int] = []


class PlanResult(BaseModel):
    steps: list[TaskStep]


class StepOutcome(BaseModel):
    step_id: int
    action: str
    status: StepStatus
    result: dict | None = None
    error: str | None = None


class UserRequest(BaseModel):
    message: str

    @property
    def is_empty(self) -> bool:
        return not self.message.strip()


class AgentResponse(BaseModel):
    status: str
    plan: list[TaskStep]
    execution: list[StepOutcome]
