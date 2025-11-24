"""Script to initialize the database with sample doctors"""
import os
from dotenv import load_dotenv
from app.models import Doctor
from app.db import get_session, init_db
from sqlmodel import select

load_dotenv()

def init_doctors():
    """Initialize the database with sample doctors"""
    # Initialize database tables
    init_db()
    
    doctors_data = [
        {
            "name": "Dr. Firoz",
            "specialty": "General Dentistry",
            "availability": '{"monday": "9:00-17:00", "tuesday": "9:00-17:00", "wednesday": "9:00-17:00", "thursday": "9:00-17:00", "friday": "9:00-17:00"}'
        },
        {
            "name": "Dr. Rahman",
            "specialty": "Orthodontics",
            "availability": '{"monday": "10:00-16:00", "tuesday": "10:00-16:00", "wednesday": "10:00-16:00", "thursday": "10:00-16:00", "friday": "10:00-16:00"}'
        },
        {
            "name": "Dr. Akter",
            "specialty": "Pediatric Dentistry",
            "availability": '{"monday": "8:00-14:00", "tuesday": "8:00-14:00", "wednesday": "8:00-14:00", "thursday": "8:00-14:00", "friday": "8:00-14:00", "saturday": "8:00-14:00"}'
        },
        {
            "name": "Dr. Begum",
            "specialty": "Cosmetic Dentistry",
            "availability": '{"monday": "11:00-19:00", "tuesday": "11:00-19:00", "wednesday": "11:00-19:00", "thursday": "11:00-19:00", "friday": "11:00-19:00"}'
        }
    ]
    
    with get_session() as session:
        # Check if doctors already exist
        existing_doctors = session.exec(select(Doctor)).all()
        if existing_doctors:
            print("Doctors already exist in the database.")
            return
        
        # Add doctors to the database
        for doctor_data in doctors_data:
            doctor = Doctor(**doctor_data)
            session.add(doctor)
        
        session.commit()
        print(f"Added {len(doctors_data)} doctors to the database.")

if __name__ == "__main__":
    init_doctors()