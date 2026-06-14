import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Job, CVVersion
from schemas import CVVersionOut, CVGenerateRequest
from services.claude_client import tailor_cv
from services.cv_builder import build_docx
from config import get_settings

router = APIRouter(prefix="/api/cv", tags=["cv"])


def _read_base_cv() -> str:
    path = get_settings().base_cv_path
    if not os.path.exists(path):
        raise HTTPException(400, "Base CV not found. Upload your CV first via POST /api/cv/base")
    with open(path) as f:
        return f.read()


@router.get("/base")
def get_base_cv():
    path = get_settings().base_cv_path
    if not os.path.exists(path):
        return {"content": ""}
    with open(path) as f:
        return {"content": f.read()}


@router.post("/base")
async def upload_base_cv(content: dict):
    """Body: {"content": "full cv text"}"""
    text = content.get("content", "").strip()
    if not text:
        raise HTTPException(400, "CV content cannot be empty")
    path = get_settings().base_cv_path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    return {"ok": True, "chars": len(text)}


@router.post("/generate", response_model=CVVersionOut)
def generate_cv(req: CVGenerateRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    base_cv = _read_base_cv()
    tailored = tailor_cv(base_cv, job.title, job.company, job.description or "")
    docx_path = build_docx(tailored, job.id)

    cv = CVVersion(job_id=job.id, content=tailored, docx_path=docx_path)
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


@router.post("/save", response_model=CVVersionOut)
def save_cv(body: dict, db: Session = Depends(get_db)):
    """Salva una versione editata manualmente senza chiamare Ollama."""
    job_id = body.get("job_id")
    content = (body.get("content") or "").strip()
    if not job_id or not content:
        raise HTTPException(400, "job_id e content sono obbligatori")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    docx_path = build_docx(content, job.id)
    cv = CVVersion(job_id=job.id, content=content, docx_path=docx_path)
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


@router.delete("/{cv_id}")
def delete_cv(cv_id: int, db: Session = Depends(get_db)):
    cv = db.query(CVVersion).filter(CVVersion.id == cv_id).first()
    if not cv:
        raise HTTPException(404, "CV not found")
    if cv.docx_path and os.path.exists(cv.docx_path):
        os.remove(cv.docx_path)
    db.delete(cv)
    db.commit()
    return {"ok": True}


@router.get("/job/{job_id}", response_model=list[CVVersionOut])
def list_cv_versions(job_id: int, db: Session = Depends(get_db)):
    return (
        db.query(CVVersion)
        .filter(CVVersion.job_id == job_id)
        .order_by(CVVersion.created_at.desc())
        .all()
    )


@router.get("/{cv_id}/download")
def download_cv(cv_id: int, db: Session = Depends(get_db)):
    cv = db.query(CVVersion).filter(CVVersion.id == cv_id).first()
    if not cv or not cv.docx_path:
        raise HTTPException(404, "CV not found")
    if not os.path.exists(cv.docx_path):
        raise HTTPException(404, "CV file missing from disk")
    filename = f"cv_{cv.job.company}_{cv.job.title}.docx".replace(" ", "_")
    return FileResponse(cv.docx_path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@router.get("/{cv_id}/content")
def get_cv_content(cv_id: int, db: Session = Depends(get_db)):
    cv = db.query(CVVersion).filter(CVVersion.id == cv_id).first()
    if not cv:
        raise HTTPException(404, "CV not found")
    return {"content": cv.content}
