import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from app.routes import appointment, voice, phone
from app.db import init_db


load_dotenv()


app = FastAPI(title="Bangla AI Receptionist", docs_url="/docs", redoc_url="/redoc")


app.include_router(appointment.router, prefix="/api")
app.include_router(voice.router)
app.include_router(phone.router, prefix="/api")


# init DB
init_db()


# serve frontend for testing
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def home():
    return {"status":"ok", "message":"Bangla AI Receptionist: visit /static/index.html"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2023-12-01T00:00:00Z"}