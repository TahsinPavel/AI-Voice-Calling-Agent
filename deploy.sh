#!/bin/bash
# Deployment script for AI Voice Receptionist

echo "Starting deployment process..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run database migrations (if any)
echo "Initializing database..."
python -c "from app.db import init_db; init_db()"

# Seed doctors data
echo "Seeding doctors data..."
python -c "from seed_doctors import seed_doctors; seed_doctors()"

# Start the application
echo "Starting application..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}