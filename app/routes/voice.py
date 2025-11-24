import os
import asyncio
import json
import base64
import io
import wave
import pyttsx3
from dotenv import load_dotenv
import google.generativeai as genai
from app.utils.ai_prompt import SYSTEM_PROMPT
from app.utils.helpers import safe_parse_json_block
from fastapi import APIRouter, WebSocket, WebSocketDisconnect


load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
print("GEMINI_API_KEY:", GEMINI_API_KEY)

router = APIRouter()

def text_to_speech_bytes(text, voice_id=1, rate=200, volume=1.0):
    """Convert text to speech and return as bytes"""
    try:
        # Initialize the text-to-speech engine
        engine = pyttsx3.init()
        
        # Get available voices
        voices = engine.getProperty('voices')
        
        # Set voice properties
        if voice_id < len(voices):
            engine.setProperty('voice', voices[voice_id].id)
        
        # Set speech rate (words per minute)
        engine.setProperty('rate', rate)
        
        # Set volume (0.0 to 1.0)
        engine.setProperty('volume', volume)
        
        # Save to BytesIO object as WAV
        audio_buffer = io.BytesIO()
        
        # Create a temporary file to capture the audio
        temp_file = "temp_speech.wav"
        engine.save_to_file(text, temp_file)
        engine.runAndWait()
        
        # Read the WAV file
        with open(temp_file, 'rb') as f:
            audio_data = f.read()
        
        # Clean up temporary file
        os.remove(temp_file)
        
        return audio_data
        
    except Exception as e:
        print(f"Error generating speech: {e}")
        return None

async def send_text_to_speech(websocket, text, voice_id=1, rate=200, volume=1.0):
    """Convert text to speech and send as audio data"""
    try:
        # Generate speech from text using pyttsx3
        audio_data = text_to_speech_bytes(text, voice_id=voice_id, rate=rate, volume=volume)
        
        if audio_data:
            # Send the audio data to the client
            await websocket.send_bytes(audio_data)
            print(f"Sent audio data: {len(audio_data)} bytes")
            
            # Also send the text for display
            await websocket.send_text(f"AI: {text}")
        else:
            # Fallback to text only if speech generation failed
            await websocket.send_text(f"AI: {text}")
        
    except Exception as e:
        print(f"Error generating speech: {e}")
        await websocket.send_text(f"AI: {text}")  # Fallback to text only

@router.websocket("/ws/ai")
async def websocket_ai(websocket: WebSocket):
    print("inside socket")
    await websocket.accept()
    print("WebSocket accepted")  # <-- log
    
    # Check if API key is available
    if not GEMINI_API_KEY:
        await websocket.send_text("Error: Gemini API key not configured")
        await websocket.close()
        return
        
    # Default voice settings
    voice_settings = {
        "voice_id": 1,
        "rate": 200,
        "volume": 1.0
    }
    
    try:
        # Configure Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Set up the model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Initialize conversation history
        conversation_history = [
            {"role": "user", "parts": ["হ্যালো, আমি ডেন্টাল চেম্বারে কল করেছি।"]},
            {"role": "model", "parts": ["হ্যালো! আমি ডেন্টাল চেম্বারের ভয়েস রেসেপশনিস্ট। আপনাকে কিভাবে সাহায্য করতে পারি?"]}
        ]
        
        # Send initial AI response with audio
        initial_response = "হ্যালো! আমি ডেন্টাল চেম্বারের ভয়েস রেসেপশনিস্ট। আপনাকে কিভাবে সাহায্য করতে পারি?"
        await send_text_to_speech(websocket, initial_response, 
                                voice_id=voice_settings["voice_id"], 
                                rate=voice_settings["rate"], 
                                volume=voice_settings["volume"])
        print("Initial response sent")
        
        async def process_user_message(message_text):
            """Process user message and generate AI response"""
            try:
                # Check if this is a voice settings command
                if message_text.startswith("/voice"):
                    parts = message_text.split()
                    if len(parts) >= 3:
                        setting = parts[1]
                        value = parts[2]
                        if setting == "voice":
                            voice_settings["voice_id"] = int(value)
                            await websocket.send_text(f"Voice changed to {value}")
                        elif setting == "rate":
                            voice_settings["rate"] = int(value)
                            await websocket.send_text(f"Speech rate changed to {value}")
                        elif setting == "volume":
                            voice_settings["volume"] = float(value) / 100.0
                            await websocket.send_text(f"Volume changed to {value}%")
                    return
                
                # Add user message to conversation history
                conversation_history.append({"role": "user", "parts": [message_text]})
                
                # Generate response using Gemini
                response = model.generate_content(conversation_history)
                
                # Add AI response to conversation history
                conversation_history.append({"role": "model", "parts": [response.text]})
                
                # Send response back to client as audio
                await send_text_to_speech(websocket, response.text,
                                        voice_id=voice_settings["voice_id"], 
                                        rate=voice_settings["rate"], 
                                        volume=voice_settings["volume"])
                print(f"AI response sent: {response.text}")
                
                # Check if response contains JSON summary data
                parsed = safe_parse_json_block(response.text)
                if parsed:
                    await websocket.send_json({
                        "type": "ai_summary",
                        "data": parsed
                    })
                    
            except Exception as e:
                print(f"Error processing user message: {e}")
                await websocket.send_text(f"Error processing message: {str(e)}")
        
        # Listen for messages from the client
        while True:
            try:
                data = await websocket.receive_text()
                print(f"Received message from client: {data}")
                
                # Process the user message
                await process_user_message(data)
                
            except WebSocketDisconnect:
                print("WebSocket disconnected by client")
                break
            except Exception as e:
                print(f"Error receiving from WebSocket: {e}")
                break
                
    except Exception as e:
        print(f"Error in websocket: {e}")
        try:
            await websocket.send_text(f"Error: {str(e)}")
        except:
            pass
        await websocket.close()