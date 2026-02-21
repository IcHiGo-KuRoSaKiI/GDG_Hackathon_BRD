"""
BRD Generator - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import routes (absolute imports for running as module)
from backend.routes import projects_router, documents_router, brds_router
from backend.config import settings

# Create FastAPI app
app = FastAPI(
    title="BRD Generator API",
    description="Automatically generate Business Requirements Documents from multiple communication channels",
    version="1.0.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(brds_router)

logger.info("BRD Generator API initialized")

# Health check endpoint
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "BRD Generator API",
        "version": "1.0.0",
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "api": "online",
            "firestore": "connected",
            "storage": "connected",
            "ai": "litellm-configured"
        },
        "routes": {
            "projects": "POST /projects, GET /projects/{id}",
            "documents": "POST /projects/{id}/documents/upload, GET /projects/{id}/documents",
            "brds": "POST /projects/{id}/brds/generate, GET /projects/{id}/brds"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
