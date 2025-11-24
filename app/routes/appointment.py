from fastapi import APIRouter, HTTPException
from sqlmodel import select
from app.db import get_session
from app.models import Appointment, CallNote


router = APIRouter()


@router.post("/book-appointment")
async def book_appointment(payload: Appointment):
    with get_session() as session:
        session.add(payload)
        session.commit()
        session.refresh(payload)
        return {"status": "ok", "data": payload}


@router.get("/appointments")
async def list_appointments():
    with get_session() as session:
        stmt = select(Appointment)
        results = session.exec(stmt).all()
        return results


@router.post("/save-note")
async def save_note(note: dict):
    # expected keys: bangla_text, english_text, raw_transcript, appointment_id
    n = CallNote(**note)
    with get_session() as session:
        session.add(n)
        session.commit()
        session.refresh(n)
        return {"status":"ok","note_id": n.id}