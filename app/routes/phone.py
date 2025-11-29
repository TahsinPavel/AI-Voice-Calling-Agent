import os
import re
import json
import time
import logging
from functools import lru_cache
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
import google.generativeai as genai
from app.utils.ai_prompt import SYSTEM_PROMPT
from app.models import Appointment, Doctor
from app.db import get_session
from sqlmodel import select

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Twilio configuration
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

# Gemini configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Twilio client
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
else:
    twilio_client = None
    logger.warning("Twilio credentials not found. Phone functionality will be disabled.")

# Configure Gemini with error handling
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("Gemini API key not found. AI functionality will be disabled.")

# Try different models in order of preference
model_names = ['gemini-2.0-flash', 'models/gemini-2.0-flash', 'gemini-flash-latest', 'models/gemini-flash-latest', 'gemini-pro-latest', 'models/gemini-pro-latest']
model = None

if GEMINI_API_KEY:
    for model_name in model_names:
        try:
            model = genai.GenerativeModel(model_name)
            # Test the model with a simple prompt
            test_response = model.generate_content("Hello, this is a test.")
            logger.info(f"Gemini model {model_name} initialized successfully")
            break
        except Exception as e:
            logger.warning(f"Error initializing Gemini model {model_name}: {e}")
            continue

    if not model:
        logger.error("Failed to initialize any Gemini model")
else:
    logger.info("Skipping Gemini model initialization due to missing API key")

router = APIRouter()

@lru_cache(maxsize=1)
def get_cached_doctor_list():
    """Get list of doctors from database with caching"""
    try:
        with get_session() as session:
            doctors = session.exec(select(Doctor)).all()
            logger.info(f"Retrieved {len(doctors)} doctors from database")
            return doctors
    except Exception as e:
        logger.error(f"Error fetching doctors: {e}")
        return []

def get_doctor_list():
    """Get list of doctors from database"""
    return get_cached_doctor_list()

def format_doctor_info(doctors):
    """Format doctor information for the AI prompt"""
    if not doctors:
        return "No doctors available at the moment."
    
    doctor_info = "Available Doctors:\n"
    for doctor in doctors:
        doctor_info += f"- {doctor.name}: {doctor.specialty}\n"
    return doctor_info

@router.post("/voice")
async def voice(request: Request):
    """Handle incoming voice calls"""
    # Get call details from Twilio
    form_data = await request.form()
    from_number = form_data.get("From", "")
    call_sid = form_data.get("CallSid", "")
    
    logger.info(f"Incoming call from {from_number} with CallSid {call_sid}")
    
    # Create TwiML response
    resp = VoiceResponse()
    
    # Check if Twilio is configured
    if not twilio_client:
        resp.say("Sorry, phone service is currently unavailable.", language="en-US", voice="Polly.Joanna")
        resp.hangup()
        return resp
    
    # Get doctor information
    doctors = get_doctor_list()
    doctor_info = format_doctor_info(doctors)
    
    # Update the system prompt with current doctor information
    enhanced_system_prompt = SYSTEM_PROMPT + f"\n\nCurrent Doctor Information:\n{doctor_info}"
    
    # Gather input from caller with a longer timeout
    gather = resp.gather(
        input="speech",
        action="/api/process_speech",
        method="POST",
        timeout=3,
        language="en-US"
    )
    
    # Play welcome message with natural speed
    gather.say("Hello! I'm the dental clinic's voice receptionist. How can I help you today?", 
               language="en-US", voice="Polly.Joanna")
    
    # If no input received, redirect to voicemail
    resp.redirect("/api/voicemail", method="GET")
    
    return resp

@router.post("/process_speech")
async def process_speech(request: Request):
    """Process speech input from caller"""
    form_data = await request.form()
    speech_result = form_data.get("SpeechResult", "")
    from_number = form_data.get("From", "")
    
    logger.info(f"Speech result: {speech_result}")
    
    resp = VoiceResponse()
    
    # Check if Twilio is configured
    if not twilio_client:
        resp.say("Sorry, phone service is currently unavailable.", language="en-US", voice="Polly.Odia Female")
        resp.hangup()
        return resp
    
    if not speech_result:
        resp.say("Sorry, I didn't understand what you said. Please try again.", 
                 language="en-US", voice="Polly.Joanna")
        resp.redirect("/api/voice", method="POST")
        return resp
    
    # Get doctor information
    doctors = get_doctor_list()
    doctor_info = format_doctor_info(doctors)
    
    # Update the system prompt with current doctor information
    enhanced_system_prompt = SYSTEM_PROMPT + f"\n\nCurrent Doctor Information:\n{doctor_info}"
    
    try:
        # Process the speech with Gemini AI
        full_prompt = f"{enhanced_system_prompt}\n\nCaller said: {speech_result}\n\nRespond appropriately in English."
        
        if model:
            # Send immediate acknowledgment to show we're processing the request
            resp.say("I'm processing your request, please wait...", language="en-US", voice="Polly.Joanna")
            
            # Reduce delay to help with rate limiting while improving response time
            time.sleep(0.1)  # Reduced from 1 second to 0.1 second
            
            response = model.generate_content(full_prompt)
            ai_response = response.text
        else:
            # Fallback response if model is not available
            ai_response = "Sorry, I'm unable to help at the moment. Please try again."
        
        logger.info(f"AI Response: {ai_response}")
        
        # Parse JSON from AI response if present
        appointment_data = None
        try:
            # Extract JSON from the response
            json_match = re.search(r'\{[^}]+\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed_data = json.loads(json_str)
                appointment_data = parsed_data.get("appointment_data")
                
                # Save appointment if data is present
                if appointment_data and isinstance(appointment_data, dict):
                    with get_session() as session:
                        appointment = Appointment(**appointment_data)
                        session.add(appointment)
                        session.commit()
                        session.refresh(appointment)
                    logger.info(f"Appointment booked: {appointment_data}")
        except Exception as e:
            logger.error(f"Error parsing appointment data: {e}")
        
        # Extract the text message (remove JSON part if present)
        display_text = ai_response
        if appointment_data is not None:
            # Remove JSON part from the display text
            json_start = ai_response.find('{')
            if json_start != -1:
                json_end = ai_response.rfind('}') + 1
                if json_end > json_start:
                    # Remove JSON block from the response
                    before_json = ai_response[:json_start].strip()
                    after_json = ai_response[json_end:].strip()
                    display_text = (before_json + " " + after_json).strip()
                    # If both parts are empty, just use a generic response
                    if not display_text:
                        display_text = "Great! Your appointment has been confirmed."
                    # Ensure we don't speak just whitespace or newlines
                    display_text = display_text.strip()
                    if not display_text:
                        display_text = "Great! Your appointment has been confirmed."
        
        # Additional cleanup to remove any JSON code blocks with backticks
        while '```' in display_text:
            first_index = display_text.find('```')
            if first_index != -1:
                last_index = display_text.find('```', first_index + 3)
                if last_index != -1:
                    display_text = display_text[:first_index] + display_text[last_index + 3:]
                else:
                    break
            else:
                break
        
        # Remove any remaining backticks
        display_text = display_text.replace('```', '').strip()
        
        # Log the display text for debugging
        logger.info(f"Display text: {display_text}")
        
        # Play AI response with natural speed (fallback when ffmpeg is not available)
        resp.say(display_text, language="en-US", voice="Polly.Joanna")
        
        # Continue conversation
        gather = resp.gather(
            input="speech",
            action="/api/process_speech",
            method="POST",
            timeout=3,
            language="en-US"
        )
        gather.say("Is there anything else I can help you with?", language="en-US", voice="Polly.Joanna")
        
    except Exception as e:
        logger.error(f"Error processing speech: {e}")
        resp.say("Sorry, there was an issue. We'll try to fix it soon.", 
                 language="en-US", voice="Polly.Joanna")
    
    return resp

@router.get("/voicemail")
async def voicemail():
    """Handle voicemail"""
    resp = VoiceResponse()
    
    # Check if Twilio is configured
    if not twilio_client:
        resp.say("Sorry, phone service is currently unavailable.", language="en-US", voice="Polly.Joanna")
        resp.hangup()
        return resp
    
    resp.say("We couldn't connect your call. Please try again later.", 
             language="en-US", voice="Polly.Joanna")
    resp.hangup()
    return resp