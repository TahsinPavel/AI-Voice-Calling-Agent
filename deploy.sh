#!/bin/bash
# Deployment script for AI Voice Receptionist

echo "Starting deployment process..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run database migrations (if any)
echo "Initializing database..."
python -c "from app.db import init_db; init_db()"

# Start the application
echo "Starting application..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}