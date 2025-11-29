import os
import asyncio
import json
import base64
import io
import time
import logging
import warnings
from functools import lru_cache
from dotenv import load_dotenv
import google.generativeai as genai
from gtts import gTTS
from pydub import AudioSegment
from pydub.utils import which
from app.utils.ai_prompt import SYSTEM_PROMPT
from app.utils.helpers import safe_parse_json_block
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.models import Doctor
from app.db import get_session
from sqlmodel import select


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
logger.info(f"GEMINI_API_KEY present: {bool(GEMINI_API_KEY)}")

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

def get_doctor_info_json(doctors):
    """Get doctor information as JSON for frontend"""
    if not doctors:
        return "[]"
    
    doctor_list = []
    for doctor in doctors:
        doctor_list.append({
            "name": doctor.name,
            "specialty": doctor.specialty
        })
    
    return json.dumps(doctor_list)

def change_audio_speed(audio_data, speed=1.0):
    """Change the speed of audio data"""
    try:
        # Suppress pydub warnings about missing ffmpeg
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Check if ffmpeg is available
            if which("ffmpeg") is None and which("avconv") is None:
                logger.warning("ffmpeg/avconv not found. Audio speed adjustment will be skipped.")
                return audio_data
            
            # Load audio from bytes
            audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            
            # Change speed by adjusting frame rate
            # Higher frame rate = faster playback
            new_sample_rate = int(audio.frame_rate * speed)
            audio_fast = audio._spawn(audio.raw_data, overrides={"frame_rate": new_sample_rate})
            audio_fast = audio_fast.set_frame_rate(audio.frame_rate)
            
            # Convert back to bytes
            buffer = io.BytesIO()
            audio_fast.export(buffer, format="mp3")
            return buffer.getvalue()
    except Exception as e:
        logger.warning(f"Error changing audio speed: {e}. Returning original audio.")
        # Return original audio if we can't change speed
        return audio_data  

async def send_text_to_speech(websocket, text, speed=1.0):
    """Convert text to speech and send as audio data"""
    try:
        # Generate speech from text using gTTS
        tts = gTTS(text=text, lang='en')  
        
        # Save to BytesIO object
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        # Read the audio data
        audio_data = audio_buffer.read()
        
        # Change speed if needed and if not using default speed
        if speed != 1.0:
            original_size = len(audio_data)
            audio_data = change_audio_speed(audio_data, speed)
            if len(audio_data) == original_size:
                logger.info("Audio speed adjustment was skipped (ffmpeg not available)")
            else:
                logger.info("Audio speed adjusted successfully")
        
        # Send the audio data to the client
        await websocket.send_bytes(audio_data)
        logger.info(f"Sent audio data: {len(audio_data)} bytes")
        
        # Also send the text for display
        await websocket.send_text(f"AI: {text}")
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        await websocket.send_text(f"AI: {text}")  # Fallback to text only

@router.websocket("/ws/ai")
async def websocket_ai(websocket: WebSocket):

    await websocket.accept()
    logger.info("WebSocket connection accepted")
    
    # Check if Gemini is configured
    if not GEMINI_API_KEY:
        await websocket.send_text("Error: Gemini API key not configured")
        await websocket.close()
        return
    
    # Get doctor information
    doctors = get_doctor_list()
    doctor_info = format_doctor_info(doctors)
    doctor_info_json = get_doctor_info_json(doctors)
    
    # Update the system prompt with current doctor information
    enhanced_system_prompt = SYSTEM_PROMPT + f"\n\nCurrent Doctor Information:\n{doctor_info}"
    
    # Initialize conversation history
    conversation_history = [
        {"role": "user", "parts": [enhanced_system_prompt]},
        {"role": "model", "parts": ["I understand. I'm ready to help as a dental receptionist."]}
    ]
    
    # Send welcome message with natural speed (fallback when ffmpeg is not available)
    welcome_message = "Hello! I'm the dental clinic's voice receptionist. How can I help you today?"
    await send_text_to_speech(websocket, welcome_message, speed=1.0)
    
    # Send doctor information to frontend
    await websocket.send_text(f"DOCTORS: {doctor_info_json}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received: {data}")
            
            if data.startswith("User: "):
                # Send immediate acknowledgment
                await websocket.send_text("AI: I've received your message and am processing it now...")
                
                user_message = data[6:]  # Remove "User: " prefix
                
                # Add user message to conversation history
                conversation_history.append({"role": "user", "parts": [user_message]})
                
                try:
                    # Generate response using Gemini
                    if model:
                        # Send immediate acknowledgment to show we're processing the request
                        await websocket.send_text("AI: I'm processing your request, please wait...")
                        
                        # Reduce delay to help with rate limiting while improving response time
                        time.sleep(0.1)  # Reduced from 1 second to 0.1 second
                        
                        chat = model.start_chat(history=conversation_history)
                        response = chat.send_message(user_message)
                        ai_response = response.text
                    else:
                        # Fallback response if model is not available
                        ai_response = "Sorry, I'm unable to help at the moment. Please try again."
                    
                    logger.info(f"AI Response: {ai_response}")
                    
                    # Add AI response to conversation history
                    conversation_history.append({"role": "model", "parts": [ai_response]})
                    
                    # Check if there's appointment data in the response
                    appointment_data = safe_parse_json_block(ai_response)
                    
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
                    
                    # Send AI response with natural speed (fallback when ffmpeg is not available)
                    if display_text:
                        await send_text_to_speech(websocket, display_text, speed=1.0)
                    
                    # If we have appointment data, save it to database
                    if appointment_data and "appointment_data" in appointment_data:
                        appt_data = appointment_data["appointment_data"]
                        if appt_data:
                            # Save appointment to database
                            try:
                                with get_session() as session:
                                    appointment = Appointment(**appt_data)
                                    session.add(appointment)
                                    session.commit()
                                    session.refresh(appointment)
                                logger.info(f"Appointment booked: {appt_data}")
                            except Exception as e:
                                logger.error(f"Error saving appointment: {e}")
                    
                except Exception as e:
                    error_msg = f"Error processing message: {str(e)}"
                    logger.error(error_msg)
                    await websocket.send_text(error_msg)
                    # Send error message to user with natural speed (fallback when ffmpeg is not available)
                    await send_text_to_speech(websocket, "Sorry, I'm unable to help at the moment. Please try again.", speed=1.0)
            
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()
        logger.info("WebSocket connection closed")
