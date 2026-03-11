"""
ClipForge AI — FastAPI Application Entry Point

Configures the FastAPI app with CORS, routers, and health check.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import router as api_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-powered podcast clipping system that identifies viral 40-60 second "
        "clips and generates professional editing blueprints."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=f"/api/{settings.api_version}")


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "0.1.0",
    }
