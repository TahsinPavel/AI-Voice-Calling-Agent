import json
from app.models import Doctor
from app.db import get_session

def seed_doctors(force_replace=False):
    """Seed the database with American doctors"""
    doctors_data = [
        {
            "name": "Dr. Smith",
            "specialty": "General Dentistry",
            "availability": json.dumps({
                "monday": ["09:00-12:00", "14:00-17:00"],
                "tuesday": ["09:00-12:00", "14:00-17:00"],
                "wednesday": ["09:00-12:00", "14:00-17:00"],
                "thursday": ["09:00-12:00", "14:00-17:00"],
                "friday": ["09:00-12:00", "14:00-17:00"],
                "saturday": ["09:00-12:00"],
                "sunday": []
            })
        },
        {
            "name": "Dr. Johnson",
            "specialty": "Orthodontics",
            "availability": json.dumps({
                "monday": ["10:00-13:00", "15:00-18:00"],
                "tuesday": ["10:00-13:00", "15:00-18:00"],
                "wednesday": ["10:00-13:00"],
                "thursday": ["10:00-13:00", "15:00-18:00"],
                "friday": ["10:00-13:00", "15:00-18:00"],
                "saturday": ["10:00-14:00"],
                "sunday": []
            })
        },
        {
            "name": "Dr. Williams",
            "specialty": "Pediatric Dentistry",
            "availability": json.dumps({
                "monday": ["08:00-12:00"],
                "tuesday": ["08:00-12:00", "14:00-17:00"],
                "wednesday": ["08:00-12:00"],
                "thursday": ["08:00-12:00", "14:00-17:00"],
                "friday": ["08:00-12:00"],
                "saturday": ["08:00-12:00"],
                "sunday": []
            })
        },
        {
            "name": "Dr. Brown",
            "specialty": "Cosmetic Dentistry",
            "availability": json.dumps({
                "monday": ["11:00-15:00", "16:00-19:00"],
                "tuesday": ["11:00-15:00"],
                "wednesday": ["11:00-15:00", "16:00-19:00"],
                "thursday": ["11:00-15:00"],
                "friday": ["11:00-15:00", "16:00-19:00"],
                "saturday": ["11:00-16:00"],
                "sunday": []
            })
        }
    ]
    
    with get_session() as session:
        # Check if doctors already exist
        existing_doctors = session.query(Doctor).all()
        if existing_doctors and not force_replace:
            # Check if the existing doctors are the old Bangladeshi ones
            old_doctor_names = ["Dr. Firoz", "Dr. Rahman", "Dr. Akter", "Dr. Begum"]
            existing_names = [doctor.name for doctor in existing_doctors]
            
            # If we have the old doctors, replace them with the new American ones
            if any(name in existing_names for name in old_doctor_names):
                print("Replacing old Bangladeshi doctors with new American doctors...")
                # Delete all existing doctors
                for doctor in existing_doctors:
                    session.delete(doctor)
                session.commit()
                
                # Add new American doctors
                for doctor_data in doctors_data:
                    doctor = Doctor(**doctor_data)
                    session.add(doctor)
                
                session.commit()
                print("Successfully replaced doctors in the database.")
            else:
                print("Doctors already exist in the database. Skipping seed.")
                return
        elif existing_doctors and force_replace:
            print("Force replacing doctors with new American doctors...")
            # Delete all existing doctors
            for doctor in existing_doctors:
                session.delete(doctor)
            session.commit()
            
            # Add new American doctors
            for doctor_data in doctors_data:
                doctor = Doctor(**doctor_data)
                session.add(doctor)
            
            session.commit()
            print("Successfully replaced doctors in the database.")
        else:
            # No doctors exist, add the new American ones
            for doctor_data in doctors_data:
                doctor = Doctor(**doctor_data)
                session.add(doctor)
            
            session.commit()
            print("Successfully seeded doctors database.")

if __name__ == "__main__":
    seed_doctors(force_replace=True)