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
        
    try:
        # Configure Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Use a simple, known working model
        model = genai.GenerativeModel('gemini-pro')
        
        # Send initial AI response with audio
        initial_response = "হ্যালো! আমি ডেন্টাল চেম্বারের ভয়েস রেসেপশনিস্ট। আপনাকে কিভাবে সাহায্য করতে পারি?"
        await send_text_to_speech(websocket, initial_response)
        print("Initial response sent")
        
        # Listen for messages from the client
        while True:
            try:
                data = await websocket.receive_text()
                print(f"Received message from client: {data}")
                
                # Simple response for testing
                if "test" in data.lower():
                    response_text = "This is a test response from the AI."
                else:
                    # Generate response using Gemini
                    try:
                        response = model.generate_content(f"Respond in Bengali: {data}")
                        response_text = response.text
                    except Exception as e:
                        print(f"Error generating content: {e}")
                        response_text = "দুঃখিত, আমি এই মুহূর্তে সাড়া দিতে পারছি না। অনুগ্রহ করে আবার চেষ্টা করুন।"
                
                # Send response back to client as audio
                await send_text_to_speech(websocket, response_text)
                print(f"AI response sent: {response_text}")
                
            except WebSocketDisconnect:
                print("WebSocket disconnected by client")
                break
            except Exception as e:
                print(f"Error receiving from WebSocket: {e}")
                await websocket.send_text(f"Error: {str(e)}")
                break
                
    except Exception as e:
        print(f"Error in websocket: {e}")
        try:
            await websocket.send_text(f"Error: {str(e)}")
        except:
            pass
        await websocket.close()