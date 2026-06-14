import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Job, Contact, Message
from schemas import MessageOut, MessageGenerateRequest
from services.claude_client import draft_linkedin_message
from config import get_settings

router = APIRouter(prefix="/api/messages", tags=["messages"])


def _read_base_cv() -> str:
    path = get_settings().base_cv_path
    if not os.path.exists(path):
        return ""
    with open(path) as f:
        return f.read()


@router.post("/generate", response_model=MessageOut)
def generate_message(req: MessageGenerateRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    contact = None
    contact_name = req.contact_name or "there"
    if req.contact_id:
        contact = db.query(Contact).filter(Contact.id == req.contact_id).first()
        if contact:
            contact_name = contact.name

    base_cv = _read_base_cv()
    text = draft_linkedin_message(
        contact_name, job.title, job.company, job.description or "", base_cv
    )

    msg = Message(
        job_id=job.id,
        contact_id=contact.id if contact else None,
        content=text,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.post("/save", response_model=MessageOut)
def save_message(body: dict, db: Session = Depends(get_db)):
    """Salva una versione editata manualmente senza chiamare Ollama."""
    job_id = body.get("job_id")
    content = (body.get("content") or "").strip()
    contact_id = body.get("contact_id")
    if not job_id or not content:
        raise HTTPException(400, "job_id e content sono obbligatori")
    if not db.query(Job).filter(Job.id == job_id).first():
        raise HTTPException(404, "Job not found")
    msg = Message(job_id=job_id, contact_id=contact_id, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.get("/job/{job_id}", response_model=list[MessageOut])
def list_messages(job_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Message)
        .filter(Message.job_id == job_id)
        .order_by(Message.created_at.desc())
        .all()
    )


@router.delete("/{message_id}")
def delete_message(message_id: int, db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(404, "Message not found")
    db.delete(msg)
    db.commit()
    return {"ok": True}
