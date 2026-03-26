from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from extensions import get_db
from project_helpers.dependencies.jwt_required import JwtRequired
from modules.job_tracker.models.job_model import JobApplicationModel, JobStatus
from modules.smart_tasks.models.task_model import TaskModel
from .router import router


@router.get("/today")
async def get_daily_brief(
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = request.state.user
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Today's tasks
    tasks_today = db.query(TaskModel).filter(
        TaskModel.user_id == user.id,
        TaskModel.is_deleted == False,
        TaskModel.due_date >= today_start,
        TaskModel.due_date < today_end,
    ).order_by(TaskModel.is_completed.asc(), TaskModel.priority.desc()).all()

    # Overdue tasks
    overdue_tasks = db.query(TaskModel).filter(
        TaskModel.user_id == user.id,
        TaskModel.is_deleted == False,
        TaskModel.is_completed == False,
        TaskModel.due_date < today_start,
    ).count()

    # Tasks completed today
    tasks_completed_today = db.query(TaskModel).filter(
        TaskModel.user_id == user.id,
        TaskModel.is_deleted == False,
        TaskModel.is_completed == True,
        TaskModel.completed_at >= today_start,
        TaskModel.completed_at < today_end,
    ).count()

    # Follow-ups due
    follow_ups = db.query(JobApplicationModel).filter(
        JobApplicationModel.user_id == user.id,
        JobApplicationModel.is_archived == False,
        JobApplicationModel.follow_up_date <= now,
        JobApplicationModel.status.notin_([JobStatus.REJECTED, JobStatus.OFFER]),
    ).order_by(JobApplicationModel.follow_up_date.asc()).limit(10).all()

    # Upcoming interviews
    interviews = db.query(JobApplicationModel).filter(
        JobApplicationModel.user_id == user.id,
        JobApplicationModel.is_archived == False,
        JobApplicationModel.status.in_([JobStatus.PHONE_SCREEN, JobStatus.INTERVIEW]),
    ).order_by(JobApplicationModel.follow_up_date.asc()).limit(5).all()

    # Application streak
    streak = 0
    for i in range(30):
        day_start = today_start - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        count = db.query(JobApplicationModel).filter(
            JobApplicationModel.user_id == user.id,
            JobApplicationModel.is_archived == False,
            JobApplicationModel.applied_date >= day_start,
            JobApplicationModel.applied_date < day_end,
        ).count()
        if count > 0:
            streak += 1
        elif i > 0:
            break

    # Total active applications
    total_applications = db.query(JobApplicationModel).filter(
        JobApplicationModel.user_id == user.id,
        JobApplicationModel.is_archived == False,
        JobApplicationModel.status.notin_([JobStatus.REJECTED]),
    ).count()

    return {
        "tasksToday": [_brief_task(t) for t in tasks_today],
        "tasksTodayCount": len(tasks_today),
        "tasksCompletedToday": tasks_completed_today,
        "overdueTasks": overdue_tasks,
        "followUps": [_brief_job(j) for j in follow_ups],
        "followUpsCount": len(follow_ups),
        "upcomingInterviews": [_brief_job(j) for j in interviews],
        "applicationStreak": streak,
        "totalActiveApplications": total_applications,
    }


def _brief_task(t: TaskModel) -> dict[str, Any]:
    return {
        "id": t.id,
        "title": t.title,
        "priority": t.priority.value if t.priority else None,
        "isCompleted": t.is_completed,
        "dueDate": t.due_date.isoformat() if t.due_date else None,
        "category": t.category,
    }


def _brief_job(j: JobApplicationModel) -> dict[str, Any]:
    return {
        "id": j.id,
        "company": j.company,
        "role": j.role,
        "status": j.status.value if j.status else None,
        "followUpDate": j.follow_up_date.isoformat() if j.follow_up_date else None,
        "appliedDate": j.applied_date.isoformat() if j.applied_date else None,
    }
