import os
import re
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
import google.generativeai as genai
from app.utils.ai_prompt import SYSTEM_PROMPT
from app.models import Appointment
from app.db import get_session
from sqlmodel import select

load_dotenv()

# Twilio configuration
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

# Gemini configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Configure Gemini with model selection
genai.configure(api_key=GEMINI_API_KEY)

# Try different models in order of preference
model_names = ['gemini-pro', 'models/gemini-pro', 'gemini-1.0-pro', 'models/gemini-1.0-pro']
model = None

for model_name in model_names:
    try:
        model = genai.GenerativeModel(model_name)
        # Test the model with a simple prompt
        test_response = model.generate_content("Hello, test")
        print(f"Successfully initialized model for phone route: {model_name}")
        break
    except Exception as e:
        print(f"Failed to initialize model {model_name} for phone route: {e}")
        continue

if model is None:
    print("Warning: Could not initialize any available Gemini model for phone route")

router = APIRouter()

# Store active calls
active_calls = {}

@router.post("/voice")
async def voice(request: Request):
    """Handle incoming voice calls"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    from_number = form_data.get("From")
    
    print(f"Incoming call from {from_number} with CallSid {call_sid}")
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Greet the caller
    response.say("হ্যালো! আমি ডেন্টাল চেম্বারের ভয়েস রেসেপশনিস্ট। আপনাকে কিভাবে সাহায্য করতে পারি?", language="bn-BD")
    
    # Gather user input
    gather = response.gather(
        input="speech",
        language="bn-BD",
        action="/api/process_speech",
        method="POST",
        timeout=5
    )
    
    # If no input, redirect to gather again
    response.redirect("/api/voice")
    
    return str(response)

@router.post("/process_speech")
async def process_speech(request: Request):
    """Process speech input from caller"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    from_number = form_data.get("From")
    speech_result = form_data.get("SpeechResult", "")
    
    print(f"Speech input from {from_number}: {speech_result}")
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Check if model is available
    if model is None:
        response.say("দুঃখিত, সিস্টেমে কিছু সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।", language="bn-BD")
        return str(response)
    
    try:
        # Process the user's request using Gemini
        prompt = f"{SYSTEM_PROMPT}\n\nUser said: {speech_result}\n\nPlease respond in Bengali and help the user with their request. If this is an appointment request, extract the relevant details."
        gemini_response = model.generate_content(prompt)
        
        # Check if this is an appointment request
        if any(keyword in speech_result.lower() for keyword in ["appointment", "booking", "book", "schedule", "অ্যাপয়েন্টমেন্ট", "বুক", "বুকিং"]):
            # Extract appointment details using Gemini
            appointment_details = extract_appointment_details_with_ai(speech_result)
            if appointment_details and appointment_details.get("patient_name") and appointment_details.get("date") and appointment_details.get("time"):
                # Book the appointment
                appointment = book_appointment(appointment_details)
                response.say(f"আপনার অ্যাপয়েন্টমেন্ট বুক করা হয়েছে। রোগীর নাম: {appointment.patient_name}, তারিখ: {appointment.date}, সময়: {appointment.time}। ধন্যবাদ!", language="bn-BD")
            else:
                # Ask for missing details
                missing_info = []
                if not appointment_details.get("patient_name"):
                    missing_info.append("নাম")
                if not appointment_details.get("date"):
                    missing_info.append("তারিখ")
                if not appointment_details.get("time"):
                    missing_info.append("সময়")
                
                response.say(f"দুঃখিত, আমি আপনার অ্যাপয়েন্টমেন্টের বিস্তারিত বুঝতে পারিনি। অনুগ্রহ করে আপনার {', '.join(missing_info)} শেয়ার করুন।", language="bn-BD")
                
                # Gather more information
                gather = response.gather(
                    input="speech",
                    language="bn-BD",
                    action="/api/process_speech",
                    method="POST",
                    timeout=5
                )
        else:
            # General response
            response.say(gemini_response.text, language="bn-BD")
        
        # Continue the conversation
        gather = response.gather(
            input="speech",
            language="bn-BD",
            action="/api/process_speech",
            method="POST",
            timeout=5
        )
        
        # If no input, end the call
        response.say("ধন্যবাদ আপনার জন্য। আবার কল করুন!", language="bn-BD")
        response.hangup()
        
    except Exception as e:
        print(f"Error processing speech: {e}")
        response.say("দুঃখিত, কিছু সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।", language="bn-BD")
    
    return str(response)

def extract_appointment_details_with_ai(text):
    """Extract appointment details using AI"""
    try:
        # Check if model is available
        if model is None:
            return {}
            
        prompt = f"""
        Extract the following information from the user's request:
        - Patient name
        - Phone number
        - Date (in YYYY-MM-DD format)
        - Time (in HH:MM format)
        - Purpose of visit
        - Urgency level (low, medium, or high)
        
        User request: {text}
        
        Return the information in JSON format with these exact keys:
        {{
            "patient_name": "...",
            "phone": "...",
            "date": "YYYY-MM-DD",
            "time": "HH:MM",
            "purpose": "...",
            "urgency_level": "..."
        }}
        
        If any information is not available, leave it as an empty string.
        """
        
        response = model.generate_content(prompt)
        
        # Try to parse the JSON from the response
        import json
        import re
        
        # Extract JSON from the response text
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            details = json.loads(json_str)
            return details
        else:
            return {}
    except Exception as e:
        print(f"Error extracting appointment details: {e}")
        return {}

def book_appointment(details):
    """Book an appointment in the database"""
    try:
        appointment = Appointment(**details)
        with get_session() as session:
            session.add(appointment)
            session.commit()
            session.refresh(appointment)
        return appointment
    except Exception as e:
        print(f"Error booking appointment: {e}")
        return None