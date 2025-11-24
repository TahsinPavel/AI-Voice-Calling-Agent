import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from app.routes import appointment, voice, phone


load_dotenv()


app = FastAPI(title="Bangla AI Receptionist", docs_url="/docs", redoc_url="/redoc")


app.include_router(appointment.router, prefix="/api")
app.include_router(voice.router)
app.include_router(phone.router, prefix="/api")


# Initialize DB
from app.db import init_db
init_db()


# Serve frontend for testing
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def home():
    return {"status":"ok", "message":"Bangla AI Receptionist: visit /static/index.html"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2023-12-01T00:00:00Z"}


@app.get("/config.js", response_class=HTMLResponse)
async def frontend_config():
    """Serve dynamic configuration to the frontend"""
    websocket_url = os.environ.get("WEBSOCKET_URL", "")
    if not websocket_url:
        # Default to relative URL if not set
        websocket_url = "/ws/ai"
    
    config_js = f"""
    // Dynamic configuration from backend
    window.WEBSOCKET_URL = "{websocket_url}";
    console.log("WebSocket URL configured from backend:", window.WEBSOCKET_URL);
    """
    return config_js


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)