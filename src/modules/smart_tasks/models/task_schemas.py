from typing import Optional
from datetime import datetime

from pydantic import BaseModel

from .task_model import TaskPriority, RecurringType


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[TaskPriority] = TaskPriority.MEDIUM
    category: Optional[str] = None
    recurring_type: Optional[RecurringType] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[TaskPriority] = None
    category: Optional[str] = None
    recurring_type: Optional[RecurringType] = None
