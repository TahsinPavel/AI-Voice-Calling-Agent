import os
import asyncio
import json
import base64
import io
import time
from dotenv import load_dotenv
import google.generativeai as genai
from gtts import gTTS
from app.utils.ai_prompt import SYSTEM_PROMPT
from app.utils.helpers import safe_parse_json_block
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.models import Doctor
from app.db import get_session
from sqlmodel import select


load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
print("GEMINI_API_KEY:", GEMINI_API_KEY)

# Configure Gemini with error handling
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Gemini API key not found. AI functionality will be disabled.")

# Try different models in order of preference
model_names = ['gemini-2.0-flash', 'models/gemini-2.0-flash', 'gemini-flash-latest', 'models/gemini-flash-latest', 'gemini-pro-latest', 'models/gemini-pro-latest']
model = None

if GEMINI_API_KEY:
    for model_name in model_names:
        try:
            model = genai.GenerativeModel(model_name)
            # Test the model with a simple prompt
            test_response = model.generate_content("Hello, this is a test.")
            print(f"Gemini model {model_name} initialized successfully")
            break
        except Exception as e:
            print(f"Error initializing Gemini model {model_name}: {e}")
            continue

    if not model:
        print("Failed to initialize any Gemini model")
else:
    print("Skipping Gemini model initialization due to missing API key")

router = APIRouter()

def get_doctor_list():
    """Get list of doctors from database"""
    try:
        with get_session() as session:
            doctors = session.exec(select(Doctor)).all()
            return doctors
    except Exception as e:
        print(f"Error fetching doctors: {e}")
        return []

def format_doctor_info(doctors):
    """Format doctor information for the AI prompt"""
    if not doctors:
        return "No doctors available at the moment."
    
    doctor_info = "Available Doctors:\n"
    for doctor in doctors:
        doctor_info += f"- {doctor.name}: {doctor.specialty}\n"
    return doctor_info

async def send_text_to_speech(websocket, text):
    """Convert text to speech and send as audio data"""
    try:
        # Generate speech from text using gTTS
        tts = gTTS(text=text, lang='bn')  # 'bn' is the language code for Bengali
        
        # Save to BytesIO object
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        # Read the audio data
        audio_data = audio_buffer.read()
        
        # Send the audio data to the client
        await websocket.send_bytes(audio_data)
        print(f"Sent audio data: {len(audio_data)} bytes")
        
        # Also send the text for display
        await websocket.send_text(f"AI: {text}")
    except Exception as e:
        print(f"Error generating speech: {e}")
        await websocket.send_text(f"AI: {text}")  # Fallback to text only

@router.websocket("/ws/ai")
async def websocket_ai(websocket: WebSocket):
    """Handle WebSocket connections for AI interaction"""
    await websocket.accept()
    print("WebSocket connection accepted")
    
    # Check if Gemini is configured
    if not GEMINI_API_KEY:
        await websocket.send_text("Error: Gemini API key not configured")
        await websocket.close()
        return
    
    # Get doctor information
    doctors = get_doctor_list()
    doctor_info = format_doctor_info(doctors)
    
    # Update the system prompt with current doctor information
    enhanced_system_prompt = SYSTEM_PROMPT + f"\n\nCurrent Doctor Information:\n{doctor_info}"
    
    # Initialize conversation history
    conversation_history = [
        {"role": "user", "parts": [enhanced_system_prompt]},
        {"role": "model", "parts": ["I understand. I'm ready to help as a Bangla-speaking dental receptionist."]}
    ]
    
    # Send welcome message
    welcome_message = "হ্যালো! আমি ডেন্টাল চেম্বারের ভয়েস রেসেপশনিস্ট। আপনাকে কিভাবে সাহায্য করতে পারি?"
    await send_text_to_speech(websocket, welcome_message)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            print(f"Received: {data}")
            
            if data.startswith("User: "):
                user_message = data[6:]  # Remove "User: " prefix
                
                # Add user message to conversation history
                conversation_history.append({"role": "user", "parts": [user_message]})
                
                try:
                    # Generate response using Gemini
                    if model:
                        # Add a small delay to help with rate limiting
                        time.sleep(1)
                        chat = model.start_chat(history=conversation_history)
                        response = chat.send_message(user_message)
                        ai_response = response.text
                    else:
                        # Fallback response if model is not available
                        ai_response = "দুঃখিত, আমি এই মুহূর্তে সাহায্য করতে পারছি না। দয়া করে পুনরায় চেষ্টা করুন।"
                    
                    print(f"AI Response: {ai_response}")
                    
                    # Add AI response to conversation history
                    conversation_history.append({"role": "model", "parts": [ai_response]})
                    
                    # Check if there's appointment data in the response
                    appointment_data = safe_parse_json_block(ai_response)
                    
                    if appointment_data and "appointment_data" in appointment_data:
                        # Send appointment confirmation
                        appt_data = appointment_data["appointment_data"]
                        if appt_data:
                            confirmation = f"আপনার অ্যাপয়েন্টমেন্ট নিশ্চিত করা হয়েছে। ডাক্তার: {appt_data.get('doctor_name', 'Not specified')}, তারিখ: {appt_data.get('date')}, সময়: {appt_data.get('time')}"
                            await send_text_to_speech(websocket, confirmation)
                    
                    # Send AI response
                    await send_text_to_speech(websocket, ai_response)
                    
                except Exception as e:
                    error_msg = f"Error processing message: {str(e)}"
                    print(error_msg)
                    await websocket.send_text(error_msg)
                    # Send error message to user
                    await send_text_to_speech(websocket, "দুঃখিত, আমি এই মুহূর্তে সাহায্য করতে পারছি না। দয়া করে পুনরায় চেষ্টা করুন।")
            
    except WebSocketDisconnect:
        print("WebSocket connection closed")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()
        print("WebSocket connection closed")