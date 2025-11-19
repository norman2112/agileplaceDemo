from typing import List
from models.task import Task, TaskStatus


def filter_tasks_by_status(tasks: List[Task], statuses: List[TaskStatus]) -> List[Task]:
    return [task for task in tasks if task.status in statuses]