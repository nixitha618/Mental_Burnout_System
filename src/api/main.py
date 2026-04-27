from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.api.routes import router
from src.config.settings import API_HOST, API_PORT, DEBUG
from src.services.scheduler import start_scheduler
from src.api.send_otp_endpoint import router as otp_router

# Voice router import
from src.api.voice_routes import router as voice_router

# Create FastAPI app
app = FastAPI(
    title="MindGuard AI - Mental Burnout Early Warning System",
    description="AI-powered system for predicting and explaining mental burnout risk",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
app.include_router(otp_router)

# CORS (WebSocket compatible)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # wildcard origin
    allow_credentials=False,      # MUST be False when allow_origins=["*"] — browsers reject the combo
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1")
app.include_router(voice_router)        # ✅ Only once — was duplicated before


@app.get("/")
async def root():
    return {
        "message": "Welcome to MindGuard AI API",
        "docs": "/docs",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/v1/health",
            "predict": "/api/v1/predict",
            "explain": "/api/v1/explain",
            "guidance": "/api/v1/guidance",
            "test": "/api/v1/test"
        }
    }

# Start email scheduler
scheduler = start_scheduler()
print("📧 Email notification scheduler started")

if __name__ == "__main__":
    print("="*50)
    print("🚀 Starting MindGuard AI API Server")
    print("="*50)
    print(f"Host: {API_HOST}")
    print(f"Port: {API_PORT}")
    print(f"Debug mode: {DEBUG}")
    print(f"Docs available at: http://{API_HOST}:{API_PORT}/docs")
    print("="*50)

    uvicorn.run(
        "src.api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG
    )