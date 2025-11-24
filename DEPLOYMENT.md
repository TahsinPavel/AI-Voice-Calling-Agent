# Production Deployment Guide

## Environment Variables

For production deployment, you need to set the following environment variables:

```
# Database configuration
DATABASE_URL=sqlite:///./appointments.db  # Or your production database URL

# Gemini API
GEMINI_API_KEY=your_gemini_api_key

# Twilio (optional, for phone functionality)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# WebSocket URL (optional, for custom WebSocket endpoint)
WEBSOCKET_URL=wss://yourdomain.com/ws/ai

# Port (optional, for custom port)
PORT=8000
```

## Deployment Platforms

### Railway

1. Connect your GitHub repository to Railway
2. Set the environment variables in the Railway dashboard
3. Set the build command to: `pip install -r requirements.txt`
4. Set the start command to: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Heroku

1. Create a `Procfile` with the following content:
   ```
   web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

2. Set the environment variables in the Heroku dashboard

### Docker

1. Build the Docker image:
   ```
   docker build -t bangla-ai-receptionist .
   ```

2. Run the container:
   ```
   docker run -p 8000:8000 -e GEMINI_API_KEY=your_key bangla-ai-receptionist
   ```

## Database Initialization

When deploying to production, make sure to run the doctor initialization script:

```bash
python init_doctors.py
```

This will populate the database with the initial set of doctors.

## SSL Configuration

For production deployment, ensure you have SSL configured for WebSocket connections. Most deployment platforms (Railway, Heroku, etc.) handle this automatically.

## Rate Limiting

The application includes basic rate limiting for the Gemini API. If you're experiencing rate limit issues, consider:

1. Upgrading your Gemini API plan
2. Increasing the delay between requests in the code (currently 1 second)
3. Using multiple API keys and rotating between them

## Monitoring

For production monitoring, consider:

1. Setting up logging to capture errors and usage patterns
2. Implementing health checks using the `/health` endpoint
3. Monitoring the database size and performance
4. Setting up alerts for API quota usage