from typing import Optional
from datetime import datetime

from pydantic import BaseModel

from .job_model import JobStatus


class JobCreate(BaseModel):
    company: str
    role: str
    link: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = "EUR"
    notes: Optional[str] = None
    status: Optional[JobStatus] = JobStatus.WISHLIST
    follow_up_date: Optional[datetime] = None
    applied_date: Optional[datetime] = None


class JobUpdate(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    link: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[JobStatus] = None
    follow_up_date: Optional[datetime] = None
    applied_date: Optional[datetime] = None


class JobStatusUpdate(BaseModel):
    status: JobStatus
