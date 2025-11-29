# Production Deployment Checklist

## Pre-deployment Checks

### 1. Environment Variables
- [ ] `GEMINI_API_KEY` is set with a valid API key
- [ ] `TWILIO_ACCOUNT_SID` is set (optional for phone functionality)
- [ ] `TWILIO_AUTH_TOKEN` is set (optional for phone functionality)
- [ ] `TWILIO_PHONE_NUMBER` is set (optional for phone functionality)
- [ ] `DATABASE_URL` is set for production database (optional, defaults to SQLite)
- [ ] `WEBSOCKET_URL` is set for custom WebSocket endpoint (optional)
- [ ] `PORT` is set for custom port (optional, defaults to 8000)

### 2. Database
- [ ] Doctors are automatically seeded when the application starts
- [ ] Database file is writable
- [ ] Database migrations are up to date

### 3. Dependencies
- [ ] All dependencies in `requirements.txt` are installed
- [ ] `ffmpeg` is available for audio processing (optional but recommended)

### 4. Network Configuration
- [ ] Port 8000 (or custom PORT) is accessible
- [ ] WebSocket connections are allowed
- [ ] SSL/HTTPS is configured for production
- [ ] CORS is properly configured

## Deployment Steps

### Railway Deployment
1. [ ] Connect GitHub repository to Railway
2. [ ] Set environment variables in Railway dashboard
3. [ ] Set build command: `pip install -r requirements.txt`
4. [ ] Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. [ ] Deploy and monitor logs

### Heroku Deployment
1. [ ] Create `Procfile` with: `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
2. [ ] Set environment variables in Heroku dashboard
3. [ ] Deploy and monitor logs

### Docker Deployment
1. [ ] Build Docker image: `docker build -t american-dental-ai-receptionist .`
2. [ ] Run container: `docker run -p 8000:8000 -e GEMINI_API_KEY=your_key american-dental-ai-receptionist`
3. [ ] Ensure environment variables are passed correctly

## Post-deployment Verification

### 1. Health Check
- [ ] Visit `/health` endpoint - should return `{"status": "healthy", "timestamp": "..."}` 
- [ ] Visit root endpoint `/` - should return welcome message

### 2. WebSocket Connection
- [ ] Visit `/static/index.html`
- [ ] Click "Start Connection" button
- [ ] Verify WebSocket connects successfully
- [ ] Verify doctor list loads correctly
- [ ] Send a test message and verify response

### 3. Voice Functionality
- [ ] Verify audio plays correctly in browser
- [ ] Verify text-to-speech conversion works in English
- [ ] Verify natural voice speed

### 4. Doctor Information
- [ ] Verify 4 American doctors are displayed in the doctor list
- [ ] Verify doctor information is correctly formatted
- [ ] Verify doctors can be referenced in conversations

### 5. Appointment Booking
- [ ] Test booking an appointment with a specific doctor
- [ ] Verify appointment data is saved to database
- [ ] Verify confirmation message is played in English

## Troubleshooting

### Common Issues
1. **WebSocket connection fails**: Check `WEBSOCKET_URL` environment variable
2. **No doctors displayed**: Verify database connection and doctor data
3. **Voice not playing**: Check browser audio permissions and `ffmpeg` installation
4. **API quota exceeded**: Upgrade Gemini API plan or implement rate limiting
5. **Twilio not working**: Verify Twilio credentials and phone number configuration

### Logs Monitoring
- [ ] Monitor application logs for errors
- [ ] Monitor Gemini API usage
- [ ] Monitor database operations
- [ ] Monitor WebSocket connections

### Performance Optimization
- [ ] Implement caching for doctor information
- [ ] Optimize database queries
- [ ] Implement connection pooling
- [ ] Monitor memory usage