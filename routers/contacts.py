import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import Job, Contact
from schemas import ContactOut, ContactCreate, ContactUpdate
from services.google_dork import (
    search_linkedin_contacts,
    build_linkedin_search_url,
    build_linkedin_direct_url,
)


def _sort_by_region(contacts: list, region: str | None) -> list:
    """
    Tier 1 — location matches region (A→Z by location)
    Tier 2 — has location but no match (A→Z by location)
    Tier 3 — no location (A→Z by name)
    """
    if not region:
        return sorted(contacts, key=lambda c: (c.location is None, (c.location or "").lower()))

    tokens = set(re.sub(r"[,/]", " ", region).lower().split())

    def _rank(c):
        loc = (c.location or "").lower()
        loc_tokens = set(re.sub(r"[,/]", " ", loc).split())
        match = bool(tokens & loc_tokens)
        has_loc = bool(loc)
        return (
            0 if match else (1 if has_loc else 2),
            loc if has_loc else (c.name or "").lower(),
        )

    return sorted(contacts, key=_rank)

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.get("/search-urls/{job_id}")
def get_search_urls(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "company": job.company,
        "google_dork": build_linkedin_search_url(job.company),
        "linkedin_search": build_linkedin_direct_url(job.company),
    }


@router.post("/find/{job_id}", response_model=list[ContactOut])
def find_contacts(job_id: int, max_results: int = 8, force: bool = False, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    existing_contacts = db.query(Contact).filter(Contact.job_id == job_id).all()
    if existing_contacts and not force:
        return _sort_by_region(existing_contacts, job.location)

    try:
        raw = search_linkedin_contacts(job.company, region=job.location, max_results=max_results)
    except Exception as e:
        raise HTTPException(502, f"Ricerca fallita: {e}")

    existing_urls = {c.linkedin_url for c in existing_contacts if c.linkedin_url}
    saved = list(existing_contacts)
    for c in raw:
        if c.get("linkedin_url") in existing_urls:
            continue
        contact = Contact(job_id=job_id, **c)
        db.add(contact)
        db.commit()
        db.refresh(contact)
        saved.append(contact)
    return _sort_by_region(saved, job.location)


@router.post("", response_model=ContactOut)
def add_contact(body: ContactCreate, db: Session = Depends(get_db)):
    if not body.name and not body.email:
        raise HTTPException(400, "Serve almeno un nome o un'email")
    job = db.query(Job).filter(Job.id == body.job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    contact = Contact(**body.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/job/{job_id}", response_model=list[ContactOut])
def list_contacts(job_id: int, db: Session = Depends(get_db)):
    return db.query(Contact).filter(Contact.job_id == job_id).all()


@router.patch("/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, body: ContactUpdate, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    if body.contacted_at_clear:
        contact.contacted_at = None
        contact.message_sent = None
        contact.cv_version_id = None
    elif body.contacted_at is not None:
        contact.contacted_at = body.contacted_at
    for field in ("message_sent", "reply_received", "cv_version_id"):
        value = getattr(body, field)
        if value is not None:
            setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    db.delete(contact)
    db.commit()
    return {"ok": True}
