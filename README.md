# Bangla AI Receptionist

A real-time AI receptionist system that can handle phone calls, book appointments, and assist customers in Bangla.

## Features

- Real-time voice interaction with callers
- Appointment booking and management
- Natural language processing in Bangla
- Text-to-speech capabilities
- Phone integration using Twilio
- AI-powered conversation handling with Google Gemini

## Prerequisites

1. Python 3.8+
2. Twilio account for phone integration
3. Google Gemini API key
4. Ngrok (for local development and testing)

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd ai-voice-receptionist
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your configuration:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_PHONE_NUMBER=your_twilio_phone_number
   DATABASE_URL=sqlite:///./appointments.db
   ```

## Usage

1. Start the server:
   ```
   python -m uvicorn app.main:app --reload
   ```

2. For phone integration, you'll need to expose your local server to the internet using ngrok:
   ```
   ngrok http 8000
   ```

3. Configure your Twilio phone number to point to your ngrok URL + `/api/voice`

## API Endpoints

- `GET /` - Health check
- `GET /static/index.html` - Web-based testing interface
- `POST /api/voice` - Handle incoming phone calls
- `POST /api/process_speech` - Process speech input
- `POST /api/book-appointment` - Book a new appointment
- `GET /api/appointments` - List all appointments
- `POST /api/save-note` - Save call notes

## How It Works

1. When a caller dials your Twilio number, the system greets them in Bangla
2. The caller can speak naturally in Bangla to request appointments or ask questions
3. The system uses Google Gemini to understand the caller's intent
4. For appointment requests, the system extracts relevant details and books the appointment
5. All interactions are stored in a SQLite database

## Customization

You can customize the AI behavior by modifying the prompt in `app/utils/ai_prompt.py`.