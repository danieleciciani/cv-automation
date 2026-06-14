from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class JobBase(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    employer_logo: Optional[str] = None
    salary: Optional[str] = None
    job_type: Optional[str] = None


class JobCreate(JobBase):
    pass


class JobOut(JobBase):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class JobStatusUpdate(BaseModel):
    status: str


class CVVersionOut(BaseModel):
    id: int
    job_id: int
    content: Optional[str] = None
    docx_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ContactBase(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone_prefix: Optional[str] = None
    phone_number: Optional[str] = None
    linkedin_url: Optional[str] = None
    location: Optional[str] = None


class ContactCreate(ContactBase):
    job_id: int


_UNSET = object()

class ContactUpdate(BaseModel):
    contacted_at: Optional[datetime] = None
    contacted_at_clear: bool = False
    message_sent: Optional[str] = None
    reply_received: Optional[str] = None
    cv_version_id: Optional[int] = None


class ContactOut(ContactBase):
    id: int
    job_id: int
    email: Optional[str] = None
    cv_version_id: Optional[int] = None
    contacted_at: Optional[datetime] = None
    message_sent: Optional[str] = None
    reply_received: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    job_id: int
    contact_id: Optional[int] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class JobSearchRequest(BaseModel):
    query: str
    locations: list[str]
    num_pages: int = 1
    country: str = "it"
    english_only: bool = False


class CVGenerateRequest(BaseModel):
    job_id: int


class MessageGenerateRequest(BaseModel):
    job_id: int
    contact_id: Optional[int] = None
    contact_name: Optional[str] = None
