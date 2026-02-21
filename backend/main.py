"""
BRD Generator - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="BRD Generator API",
    description="Automatically generate Business Requirements Documents from multiple communication channels",
    version="1.0.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local Next.js dev
        "https://*.vercel.app",    # Vercel preview deployments
        # Add production frontend URL here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            # TODO: Add Firestore health check
            # TODO: Add Storage health check
            # TODO: Add Gemini API health check
        },
    }

# TODO: Add routes
# - POST /projects - Create project
# - POST /documents/upload - Upload documents
# - GET /documents/{project_id} - List documents
# - POST /brds/generate - Generate BRD
# - GET /brds/{brd_id} - Get BRD

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
