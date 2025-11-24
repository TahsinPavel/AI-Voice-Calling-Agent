import os
import asyncio
import json
import base64
import io
from dotenv import load_dotenv
import google.generativeai as genai
from gtts import gTTS
from app.utils.ai_prompt import SYSTEM_PROMPT
from app.utils.helpers import safe_parse_json_block
from fastapi import APIRouter, WebSocket, WebSocketDisconnect


load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
print("GEMINI_API_KEY:", GEMINI_API_KEY)

router = APIRouter()

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
    print("inside socket")
    await websocket.accept()
    print("WebSocket accepted")  # <-- log
    
    # Check if API key is available
    if not GEMINI_API_KEY:
        await websocket.send_text("Error: Gemini API key not configured")
        await websocket.close()
        return
        
    # Default voice settings (for gTTS, these are limited)
    voice_settings = {
        "lang": "bn",  # Bengali
        "slow": False
    }
    
    try:
        # Configure Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Set up the model (using gemini-1.0-pro which is more widely available)
        model = genai.GenerativeModel('gemini-1.0-pro')
        
        # Initialize conversation history
        conversation_history = [
            {"role": "user", "parts": ["হ্যালো, আমি ডেন্টাল চেম্বারে কল করেছি।"]},
            {"role": "model", "parts": ["হ্যালো! আমি ডেন্টাল চেম্বারের ভয়েস রেসেপশনিস্ট। আপনাকে কিভাবে সাহায্য করতে পারি?"]}
        ]
        
        # Send initial AI response with audio
        initial_response = "হ্যালো! আমি ডেন্টাল চেম্বারের ভয়েস রেসেপশনিস্ট। আপনাকে কিভাবে সাহায্য করতে পারি?"
        await send_text_to_speech(websocket, initial_response)
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
                        if setting == "speed":
                            voice_settings["slow"] = (value.lower() == "slow")
                            await websocket.send_text(f"Speech speed changed to {value}")
                    return
                
                # Add user message to conversation history
                conversation_history.append({"role": "user", "parts": [message_text]})
                
                # Generate response using Gemini
                response = model.generate_content(conversation_history)
                
                # Add AI response to conversation history
                conversation_history.append({"role": "model", "parts": [response.text]})
                
                # Send response back to client as audio
                await send_text_to_speech(websocket, response.text)
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