from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Appointment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_name: str
    phone: str
    date: str
    time: str
    purpose: Optional[str] = None
    urgency_level: Optional[str] = "low"
    doctor_name: Optional[str] = None  # Add doctor name
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CallNote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    appointment_id: Optional[int] = None
    bangla_text: str
    english_text: str
    raw_transcript: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Doctor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    specialty: str
    availability: str  # JSON string of availability schedule
    created_at: datetime = Field(default_factory=datetime.utcnow)