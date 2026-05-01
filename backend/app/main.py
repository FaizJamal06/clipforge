"""
ClipForge AI — FastAPI Application Entry Point

Configures the FastAPI app with security middleware, CORS, routers, and health check.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import router as api_router
from app.api.waitlist import router as waitlist_router
from app.database import engine, Base
from app.models.video import ProcessedVideo
from app.models.waitlist import WaitlistEntry  # ensure table is created
from app.middleware import RateLimitMiddleware, SecurityHeadersMiddleware, APIKeyMiddleware

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the database tables automatically on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-powered podcast clipping system that identifies viral 40-60 second "
        "clips and generates professional editing blueprints."
    ),
    version="0.1.0",
    # Disable docs in production
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# ----- Security Middleware (order matters: outermost runs first) ----- #

# 1. Security headers on ALL responses
app.add_middleware(SecurityHeadersMiddleware)

# 2. Rate limiting per IP
app.add_middleware(RateLimitMiddleware)

# 3. Optional API key authentication
app.add_middleware(APIKeyMiddleware)

# 4. CORS — tightened from allow_methods=["*"] / allow_headers=["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)

# Include API routes
app.include_router(api_router, prefix=f"/api/{settings.api_version}")
app.include_router(waitlist_router, prefix=f"/api/{settings.api_version}")


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "0.1.0",
    }
