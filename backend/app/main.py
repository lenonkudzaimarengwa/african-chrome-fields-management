"""
Main FastAPI Application
African Chrome Fields Management System
Entry point for the backend API server
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging
from contextlib import asynccontextmanager
from datetime import datetime

# Import database and models
from app.database import engine, init_db, get_db, check_database_connection
from app.models import Base

# Import routers (we'll create these next)
# from app.routers import vehicles, fuel, ore_loads, equipment, workers, shifts, incidents, spares

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# LIFESPAN CONTEXT (Startup/Shutdown)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events
    """
    # STARTUP: Initialize database
    logger.info("🚀 Starting African Chrome Fields Management System...")
    try:
        init_db()
        db_connected = await check_database_connection()
        if db_connected:
            logger.info("✅ Database initialized and connected successfully")
        else:
            logger.error("❌ Database connection failed - some features may not work")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    yield  # Application runs here
    
    # SHUTDOWN: Cleanup
    logger.info("🛑 Shutting down African Chrome Fields Management System...")
    logger.info("✅ Shutdown complete")

# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="African Chrome Fields Management API",
    description="Complete backend API for mining operations management",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# GLOBAL EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with custom format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "error_code": "INTERNAL_SERVER_ERROR",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/", tags=["System"])
def read_root():
    """API root endpoint"""
    return {
        "name": "African Chrome Fields Management API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs",
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/api/health", tags=["System"])
async def health_check():
    """Check API health status"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/health/db", tags=["System"])
async def database_health():
    """Check database connection status"""
    is_connected = await check_database_connection()
    return {
        "database": "connected" if is_connected else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# SYSTEM STATISTICS ENDPOINTS
# ============================================================================

@app.get("/api/stats/overview", tags=["Statistics"])
def get_system_overview(db: Session = Depends(get_db)):
    """Get overall system statistics"""
    from app.models import Vehicle, OreLoad, Worker, ShiftLog, Incident, Equipment
    
    try:
        total_vehicles = db.query(Vehicle).count()
        operational_vehicles = db.query(Vehicle).filter(Vehicle.status == "operational").count()
        total_equipment = db.query(Equipment).count()
        active_equipment = db.query(Equipment).filter(Equipment.status == "working").count()
        total_workers = db.query(Worker).count()
        total_loads = db.query(OreLoad).count()
        active_shifts = db.query(ShiftLog).filter(ShiftLog.status == "active").count()
        today_incidents = db.query(Incident).filter(
            Incident.date >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        return {
            "success": True,
            "data": {
                "vehicles": {
                    "total": total_vehicles,
                    "operational": operational_vehicles
                },
                "equipment": {
                    "total": total_equipment,
                    "active": active_equipment
                },
                "workforce": {
                    "total": total_workers,
                    "active_shifts": active_shifts
                },
                "operations": {
                    "total_loads": total_loads,
                    "incidents_today": today_incidents
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch statistics"
        )

# ============================================================================
# ROUTER IMPORTS (To be created)
# ============================================================================

# Uncomment these once router files are created:
# app.include_router(vehicles.router, prefix="/api/vehicles", tags=["Vehicles"])
# app.include_router(fuel.router, prefix="/api/fuel", tags=["Fuel"])
# app.include_router(ore_loads.router, prefix="/api/ore-loads", tags=["Ore Loads"])
# app.include_router(equipment.router, prefix="/api/equipment", tags=["Equipment"])
# app.include_router(workers.router, prefix="/api/workers", tags=["Workers"])
# app.include_router(shifts.router, prefix="/api/shifts", tags=["Shifts"])
# app.include_router(incidents.router, prefix="/api/incidents", tags=["Incidents"])
# app.include_router(spares.router, prefix="/api/spares", tags=["Spare Parts"])

# ============================================================================
# DEBUG ROUTE (Development only - remove in production)
# ============================================================================

@app.get("/api/debug/tables", tags=["Debug"])
def debug_tables(db: Session = Depends(get_db)):
    """List all database tables and row counts (DEBUG ONLY)"""
    from app.models import (
        Vehicle, FuelLog, OreLoad, WeighbridgeTicket,
        Equipment, EquipmentInspection, MaintenanceLog,
        Worker, ShiftLog, Incident,
        Spare, SpareUsage
    )
    
    tables = {
        "vehicles": db.query(Vehicle).count(),
        "fuel_logs": db.query(FuelLog).count(),
        "ore_loads": db.query(OreLoad).count(),
        "weighbridge_tickets": db.query(WeighbridgeTicket).count(),
        "equipment": db.query(Equipment).count(),
        "equipment_inspections": db.query(EquipmentInspection).count(),
        "maintenance_logs": db.query(MaintenanceLog).count(),
        "workers": db.query(Worker).count(),
        "shift_logs": db.query(ShiftLog).count(),
        "incidents": db.query(Incident).count(),
        "spares": db.query(Spare).count(),
        "spare_usage": db.query(SpareUsage).count(),
    }
    
    return {
        "success": True,
        "data": tables,
        "total_records": sum(tables.values())
    }

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Run with: python -m uvicorn app.main:app --reload
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
