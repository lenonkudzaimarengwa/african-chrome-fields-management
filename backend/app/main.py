"""
FastAPI Main Application Entry Point
African Chrome Fields Management System
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Application lifecycle events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("🚀 African Chrome Fields Management System starting up...")
    yield
    # Shutdown
    logger.info("🛑 Shutting down application...")

# Initialize FastAPI app
app = FastAPI(
    title=os.getenv("API_TITLE", "African Chrome Fields Management System"),
    description="Offline-first management system for mining operations",
    version=os.getenv("API_VERSION", "1.0.0"),
    lifespan=lifespan
)

# Setup CORS (Cross-Origin Resource Sharing)
# This allows the frontend (Vue.js) running on different domain/port to talk to this backend
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

logger.info(f"✅ CORS configured for: {FRONTEND_URL}")

# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for monitoring and Docker health checks.
    Returns 200 if the API is running.
    """
    return {
        "status": "healthy",
        "message": "African Chrome Fields API is running",
        "version": os.getenv("API_VERSION", "1.0.0")
    }

# ============================================================================
# ROOT ENDPOINT
# ============================================================================
@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint. Returns API information.
    """
    return {
        "name": "African Chrome Fields Management System",
        "description": "Offline-first management system for mining operations",
        "version": os.getenv("API_VERSION", "1.0.0"),
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "fleet": "/api/v1/fleet",
            "operations": "/api/v1/operations",
            "inventory": "/api/v1/inventory",
            "hr": "/api/v1/hr",
            "sync": "/api/v1/sync"
        }
    }

# ============================================================================
# PLACEHOLDER ROUTES (Will be replaced with actual implementations)
# ============================================================================

@app.get("/api/v1/fleet", tags=["Fleet Management"])
async def get_fleet():
    """Get all fleet/truck data - PLACEHOLDER"""
    return {"message": "Fleet endpoints coming soon"}

@app.get("/api/v1/operations", tags=["Operations"])
async def get_operations():
    """Get all operations data - PLACEHOLDER"""
    return {"message": "Operations endpoints coming soon"}

@app.get("/api/v1/inventory", tags=["Inventory"])
async def get_inventory():
    """Get all inventory data - PLACEHOLDER"""
    return {"message": "Inventory endpoints coming soon"}

@app.get("/api/v1/hr", tags=["HR & Workforce"])
async def get_hr():
    """Get all HR data - PLACEHOLDER"""
    return {"message": "HR endpoints coming soon"}

@app.post("/api/v1/sync", tags=["Sync"])
async def sync_offline_data(data: dict):
    """
    Sync endpoint for offline data.
    Tablets/desktops POST their local changes here when they reconnect to internet.
    PLACEHOLDER - will implement conflict resolution logic.
    """
    return {"message": "Sync endpoint coming soon", "received_items": len(data)}

# ============================================================================
# ERROR HANDLING
# ============================================================================

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle any unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "detail": "Internal server error",
        "type": type(exc).__name__
    }

# ============================================================================
# STARTUP LOG
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting African Chrome Fields Management System...")
    logger.info(f"API Documentation available at: http://localhost:8000/docs")
    logger.info(f"Database URL: {os.getenv('DATABASE_URL', 'Not configured')}")
