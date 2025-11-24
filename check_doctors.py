"""Script to check doctors in the database"""
import os
from dotenv import load_dotenv
from app.models import Doctor
from app.db import get_session
from sqlmodel import select

load_dotenv()

def check_doctors():
    """Check doctors in the database"""
    with get_session() as session:
        doctors = session.exec(select(Doctor)).all()
        if doctors:
            print(f"Found {len(doctors)} doctors in the database:")
            for doctor in doctors:
                print(f"- {doctor.name}: {doctor.specialty}")
        else:
            print("No doctors found in the database.")

if __name__ == "__main__":
    check_doctors()