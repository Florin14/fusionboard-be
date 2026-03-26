from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from extensions import get_db
from project_helpers.dependencies.jwt_required import JwtRequired
from ..models.task_model import TaskModel, TaskPriority, RecurringType
from ..models.task_schemas import TaskCreate, TaskUpdate
from .router import router


@router.get("")
async def list_tasks(
    request: Request,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    completed: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = request.state.user
    query = db.query(TaskModel).filter(
        TaskModel.user_id == user.id,
        TaskModel.is_deleted == False,
    )
    if priority:
        query = query.filter(TaskModel.priority == priority)
    if category:
        query = query.filter(TaskModel.category == category)
    if completed is not None:
        query = query.filter(TaskModel.is_completed == completed)

    total = query.count()
    tasks = query.order_by(
        TaskModel.is_completed.asc(),
        TaskModel.due_date.asc().nullslast(),
        TaskModel.priority.desc(),
    ).offset(offset).limit(limit).all()

    return {
        "data": [_task_to_dict(t) for t in tasks],
        "total": total,
    }


@router.post("", status_code=201)
async def create_task(
    body: TaskCreate,
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = request.state.user
    task = TaskModel(
        user_id=user.id,
        title=body.title,
        description=body.description,
        due_date=body.due_date,
        priority=body.priority,
        category=body.category,
        recurring_type=body.recurring_type,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


@router.get("/today")
async def get_today_tasks(
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    user = request.state.user
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    tasks = db.query(TaskModel).filter(
        TaskModel.user_id == user.id,
        TaskModel.is_deleted == False,
        TaskModel.due_date >= today_start,
        TaskModel.due_date < today_end,
    ).order_by(
        TaskModel.is_completed.asc(),
        TaskModel.priority.desc(),
    ).all()

    return [_task_to_dict(t) for t in tasks]


@router.get("/categories")
async def get_categories(
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> list[str]:
    user = request.state.user
    rows = db.query(TaskModel.category).filter(
        TaskModel.user_id == user.id,
        TaskModel.is_deleted == False,
        TaskModel.category.isnot(None),
    ).distinct().all()
    return sorted([r[0] for r in rows if r[0]])


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = request.state.user
    task = _get_task(db, task_id, user.id)
    return _task_to_dict(task)


@router.put("/{task_id}")
async def update_task(
    task_id: int,
    body: TaskUpdate,
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = request.state.user
    task = _get_task(db, task_id, user.id)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(task, field, value)

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


@router.patch("/{task_id}/complete")
async def toggle_complete(
    task_id: int,
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = request.state.user
    task = _get_task(db, task_id, user.id)

    task.is_completed = not task.is_completed
    task.completed_at = datetime.utcnow() if task.is_completed else None
    task.updated_at = datetime.utcnow()

    result = _task_to_dict(task)

    # If recurring and just completed, create next occurrence
    if task.is_completed and task.recurring_type:
        next_due = None
        if task.due_date:
            if task.recurring_type == RecurringType.DAILY:
                next_due = task.due_date + timedelta(days=1)
            elif task.recurring_type == RecurringType.WEEKLY:
                next_due = task.due_date + timedelta(weeks=1)
            elif task.recurring_type == RecurringType.MONTHLY:
                next_due = task.due_date + timedelta(days=30)

        next_task = TaskModel(
            user_id=user.id,
            title=task.title,
            description=task.description,
            due_date=next_due,
            priority=task.priority,
            category=task.category,
            recurring_type=task.recurring_type,
            recurring_parent_id=task.recurring_parent_id or task.id,
        )
        db.add(next_task)

    db.commit()
    return result


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = request.state.user
    task = _get_task(db, task_id, user.id)
    task.is_deleted = True
    task.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Task deleted"}


def _get_task(db: Session, task_id: int, user_id: int) -> TaskModel:
    task = db.query(TaskModel).filter(
        TaskModel.id == task_id,
        TaskModel.user_id == user_id,
        TaskModel.is_deleted == False,
    ).first()
    if not task:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _task_to_dict(task: TaskModel) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "dueDate": task.due_date.isoformat() if task.due_date else None,
        "priority": task.priority.value if task.priority else None,
        "category": task.category,
        "isCompleted": task.is_completed,
        "completedAt": task.completed_at.isoformat() if task.completed_at else None,
        "recurringType": task.recurring_type.value if task.recurring_type else None,
        "createdAt": task.created_at.isoformat() if task.created_at else None,
        "updatedAt": task.updated_at.isoformat() if task.updated_at else None,
    }
