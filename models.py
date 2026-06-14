from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String)
    description = Column(Text)
    source_url = Column(String)
    employer_logo = Column(String)
    salary = Column(String)
    job_type = Column(String)
    status = Column(String, default="discovered")
    created_at = Column(DateTime, default=datetime.utcnow)

    cv_versions = relationship("CVVersion", back_populates="job", cascade="all, delete")
    contacts = relationship("Contact", back_populates="job", cascade="all, delete")
    messages = relationship("Message", back_populates="job", cascade="all, delete")


class CVVersion(Base):
    __tablename__ = "cv_versions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    content = Column(Text)
    docx_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="cv_versions")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    name = Column(String)
    role = Column(String)
    email = Column(String)
    phone_prefix = Column(String)
    phone_number = Column(String)
    linkedin_url = Column(String)
    location = Column(String)
    cv_version_id = Column(Integer, ForeignKey("cv_versions.id"), nullable=True)
    contacted_at = Column(DateTime)
    message_sent = Column(Text)
    reply_received = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="contacts")
    messages = relationship("Message", back_populates="contact")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="messages")
    contact = relationship("Contact", back_populates="messages")
