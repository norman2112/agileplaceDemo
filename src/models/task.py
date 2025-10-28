from enum import Enum
from pydantic import BaseModel


class TaskStatus(str, Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    BLOCKED = "Blocked"
    COMPLETED = "Completed"


class Task(BaseModel):
    id: int
    title: str
    status: TaskStatus