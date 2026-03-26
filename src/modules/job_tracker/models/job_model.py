import enum
from datetime import datetime

from sqlalchemy import Column, BigInteger, String, Text, Integer, Boolean, DateTime, Enum, ForeignKey

from extensions import BaseModel


class JobStatus(str, enum.Enum):
    WISHLIST = "WISHLIST"
    APPLIED = "APPLIED"
    PHONE_SCREEN = "PHONE_SCREEN"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"


class JobApplicationModel(BaseModel):
    __tablename__ = "job_applications"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    company = Column(String(200), nullable=False)
    role = Column(String(200), nullable=False)
    link = Column(String(500), nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String(10), default="EUR")
    notes = Column(Text, nullable=True)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.WISHLIST)
    follow_up_date = Column(DateTime, nullable=True)
    applied_date = Column(DateTime, nullable=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
