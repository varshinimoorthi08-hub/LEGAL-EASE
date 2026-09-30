from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.routes import router


# ---------------------------------------------------------
# Application settings
# ---------------------------------------------------------

settings = get_settings()


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="LegalEase API",
    description=(
        "Backend API for LegalEase — an AI-powered legal "
        "document drafting and export application."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------
# Allows the Streamlit frontend to communicate with
# the FastAPI backend during local development.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# API routes
# ---------------------------------------------------------

app.include_router(router)


# ---------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------

@app.get("/", tags=["System"])
def root():
    """
    Basic API information endpoint.
    """
    return {
        "name": settings.app_name,
        "status": "running",
        "message": "LegalEase backend is running successfully.",
        "docs": "/docs",
    }


# ---------------------------------------------------------
# Health-check endpoint
# ---------------------------------------------------------

@app.get("/health", tags=["System"])
def health_check():
    """
    Returns the current backend and AI configuration status.
    """

    return {
        "status": "healthy",
        "app": settings.app_name,
        "demo_mode": settings.demo_mode,
        "gemini_model": settings.gemini_model,
        "gemini_configured": bool(settings.gemini_api_key),
    }