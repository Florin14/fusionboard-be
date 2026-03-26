from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from extensions import get_db
from project_helpers.dependencies.jwt_required import JwtRequired
from ..models.job_model import JobApplicationModel, JobStatus
from ..models.job_schemas import JobCreate, JobUpdate, JobStatusUpdate
from .router import router


@router.get("")
async def list_jobs(
    request: Request,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = request.state.user
    query = db.query(JobApplicationModel).filter(
        JobApplicationModel.user_id == user.id,
        JobApplicationModel.is_archived == False,
    )
    if status:
        query = query.filter(JobApplicationModel.status == status)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (JobApplicationModel.company.ilike(like)) | (JobApplicationModel.role.ilike(like))
        )
    total = query.count()
    jobs = query.order_by(JobApplicationModel.updated_at.desc()).offset(offset).limit(limit).all()
    return {
        "data": [_job_to_dict(j) for j in jobs],
        "total": total,
    }


@router.post("", status_code=201)
async def create_job(
    body: JobCreate,
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = request.state.user
    job = JobApplicationModel(
        user_id=user.id,
        company=body.company,
        role=body.role,
        link=body.link,
        salary_min=body.salary_min,
        salary_max=body.salary_max,
        salary_currency=body.salary_currency,
        notes=body.notes,
        status=body.status,
        follow_up_date=body.follow_up_date,
        applied_date=body.applied_date or (datetime.utcnow() if body.status == JobStatus.APPLIED else None),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_to_dict(job)


@router.get("/stats")
async def get_job_stats(
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = request.state.user
    base = db.query(JobApplicationModel).filter(
        JobApplicationModel.user_id == user.id,
        JobApplicationModel.is_archived == False,
    )

    counts = {}
    for s in JobStatus:
        counts[s.value] = base.filter(JobApplicationModel.status == s).count()

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    follow_ups_due = base.filter(
        JobApplicationModel.follow_up_date <= datetime.utcnow(),
        JobApplicationModel.status.notin_([JobStatus.REJECTED, JobStatus.OFFER]),
    ).count()

    upcoming_interviews = base.filter(
        JobApplicationModel.status.in_([JobStatus.PHONE_SCREEN, JobStatus.INTERVIEW]),
    ).order_by(JobApplicationModel.follow_up_date.asc()).limit(5).all()

    # Weekly streak: consecutive days with at least one application
    streak = 0
    for i in range(30):
        day_start = today - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        count = base.filter(
            JobApplicationModel.applied_date >= day_start,
            JobApplicationModel.applied_date < day_end,
        ).count()
        if count > 0:
            streak += 1
        elif i > 0:
            break

    # This week applications
    week_start = today - timedelta(days=today.weekday())
    this_week = base.filter(
        JobApplicationModel.applied_date >= week_start,
    ).count()

    return {
        "counts": counts,
        "total": sum(counts.values()),
        "followUpsDue": follow_ups_due,
        "upcomingInterviews": [_job_to_dict(j) for j in upcoming_interviews],
        "streak": streak,
        "thisWeek": this_week,
    }


@router.get("/{job_id}")
async def get_job(
    job_id: int,
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = request.state.user
    job = db.query(JobApplicationModel).filter(
        JobApplicationModel.id == job_id,
        JobApplicationModel.user_id == user.id,
    ).first()
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_dict(job)


@router.put("/{job_id}")
async def update_job(
    job_id: int,
    body: JobUpdate,
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = request.state.user
    job = db.query(JobApplicationModel).filter(
        JobApplicationModel.id == job_id,
        JobApplicationModel.user_id == user.id,
    ).first()
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(job, field, value)

    if body.status == JobStatus.APPLIED and not job.applied_date:
        job.applied_date = datetime.utcnow()

    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return _job_to_dict(job)


@router.patch("/{job_id}/status")
async def update_job_status(
    job_id: int,
    body: JobStatusUpdate,
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = request.state.user
    job = db.query(JobApplicationModel).filter(
        JobApplicationModel.id == job_id,
        JobApplicationModel.user_id == user.id,
    ).first()
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = body.status
    if body.status == JobStatus.APPLIED and not job.applied_date:
        job.applied_date = datetime.utcnow()
    if body.status in (JobStatus.APPLIED, JobStatus.PHONE_SCREEN) and not job.follow_up_date:
        job.follow_up_date = datetime.utcnow() + timedelta(days=5)
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return _job_to_dict(job)


@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    request: Request,
    _user=Depends(JwtRequired()),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = request.state.user
    job = db.query(JobApplicationModel).filter(
        JobApplicationModel.id == job_id,
        JobApplicationModel.user_id == user.id,
    ).first()
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")

    job.is_archived = True
    job.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Job archived"}


def _job_to_dict(job: JobApplicationModel) -> dict[str, Any]:
    return {
        "id": job.id,
        "company": job.company,
        "role": job.role,
        "link": job.link,
        "salaryMin": job.salary_min,
        "salaryMax": job.salary_max,
        "salaryCurrency": job.salary_currency,
        "notes": job.notes,
        "status": job.status.value if job.status else None,
        "followUpDate": job.follow_up_date.isoformat() if job.follow_up_date else None,
        "appliedDate": job.applied_date.isoformat() if job.applied_date else None,
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "updatedAt": job.updated_at.isoformat() if job.updated_at else None,
    }
