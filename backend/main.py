# Load env first so OPENROUTER_API_KEY and others are set before any service imports
import config as _config
_config.load_env()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# Import routes (they use config for API key)
from routes import chat, upload, analysis, wri
from database import init_db

# Create FastAPI app
app = FastAPI(
    title="Water Stewardship Agent API",
    description="AI-powered water stewardship chatbot system",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and log API key status
@app.on_event("startup")
async def startup_event():
    await init_db()
    key = _config.get_openrouter_api_key()
    if not key:
        print("OpenRouter API key: NOT SET — add OPENROUTER_API_KEY to backend/.env")
    else:
        print("OpenRouter API key: loaded from backend/.env")

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(wri.router, prefix="/api/wri", tags=["wri"])

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Water Stewardship Agent API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )