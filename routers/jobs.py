from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Job
from schemas import JobOut, JobStatusUpdate, JobSearchRequest
from services.jsearch import search_jobs

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

VALID_STATUSES = {"discovered", "applied", "contacted", "reply", "rejected"}


@router.post("/search", response_model=list[JobOut])
async def search_and_save(req: JobSearchRequest, db: Session = Depends(get_db)):
    try:
        raw_jobs = await search_jobs(req.query, req.locations, req.num_pages, req.country, req.english_only)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"JSearch API error: {e}")
    saved = []
    for j in raw_jobs:
        existing = db.query(Job).filter(Job.source_url == j["source_url"]).first()
        if existing:
            saved.append(existing)
            continue
        job = Job(**j)
        db.add(job)
        db.commit()
        db.refresh(job)
        saved.append(job)
    saved.sort(key=lambda j: (-j.created_at.timestamp(), (j.company or "").lower()))
    return saved


@router.get("", response_model=list[JobOut])
def list_jobs(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Job)
    if status:
        q = q.filter(Job.status == status)
    return q.order_by(Job.created_at.desc()).all()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.patch("/{job_id}/status", response_model=JobOut)
def update_status(job_id: int, body: JobStatusUpdate, db: Session = Depends(get_db)):
    if body.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Choose from: {VALID_STATUSES}")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    job.status = body.status
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    db.delete(job)
    db.commit()
    return {"ok": True}
