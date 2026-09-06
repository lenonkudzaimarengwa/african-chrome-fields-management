"""
Fuel Management API Routes
Handles all fuel logging and consumption tracking
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import FuelLog, Vehicle
from app.schemas import FuelLogCreate, FuelLogResponse

router = APIRouter()

# ============================================================================
# CREATE FUEL LOG
# ============================================================================

@router.post("/", response_model=FuelLogResponse, status_code=status.HTTP_201_CREATED)
def create_fuel_log(fuel_log: FuelLogCreate, db: Session = Depends(get_db)):
    """
    Log fuel consumption for a vehicle.
    
    - **vehicle_id**: ID of the vehicle
    - **fuel_amount**: Liters of fuel added
    - **cost**: Cost of fuel in local currency
    - **odometer_reading**: Current odometer reading in km
    - **notes**: Optional notes about the fuel log
    """
    # Verify vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == fuel_log.vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {fuel_log.vehicle_id} not found"
        )
    
    # Create fuel log
    db_fuel_log = FuelLog(**fuel_log.dict())
    db.add(db_fuel_log)
    
    # Update vehicle's current fuel level
    vehicle.current_fuel += fuel_log.fuel_amount
    if vehicle.current_fuel > vehicle.fuel_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel amount would exceed tank capacity ({vehicle.fuel_capacity}L)"
        )
    
    db.commit()
    db.refresh(db_fuel_log)
    
    return db_fuel_log

# ============================================================================
# GET ALL FUEL LOGS
# ============================================================================

@router.get("/", response_model=List[FuelLogResponse])
def get_fuel_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    vehicle_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get all fuel logs with pagination and optional filtering.
    
    - **skip**: Number of records to skip
    - **limit**: Maximum records to return
    - **vehicle_id**: Optional filter by vehicle ID
    """
    query = db.query(FuelLog)
    
    if vehicle_id:
        query = query.filter(FuelLog.vehicle_id == vehicle_id)
    
    logs = query.order_by(desc(FuelLog.date)).offset(skip).limit(limit).all()
    return logs

# ============================================================================
# GET FUEL LOG BY ID
# ============================================================================

@router.get("/{log_id}", response_model=FuelLogResponse)
def get_fuel_log(log_id: int, db: Session = Depends(get_db)):
    """
    Get a specific fuel log by ID.
    """
    log = db.query(FuelLog).filter(FuelLog.id == log_id).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fuel log with ID {log_id} not found"
        )
    
    return log

# ============================================================================
# GET FUEL LOGS FOR VEHICLE
# ============================================================================

@router.get("/vehicle/{vehicle_id}", response_model=List[FuelLogResponse])
def get_vehicle_fuel_logs(
    vehicle_id: int,
    days: int = Query(30, ge=1, le=365),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get fuel logs for a specific vehicle from the last N days.
    
    - **vehicle_id**: ID of the vehicle
    - **days**: Number of days to look back (default 30)
    - **skip**: Number of records to skip
    - **limit**: Maximum records to return
    """
    # Verify vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {vehicle_id} not found"
        )
    
    # Get logs from the last N days
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    logs = db.query(FuelLog).filter(
        (FuelLog.vehicle_id == vehicle_id) &
        (FuelLog.date >= cutoff_date)
    ).order_by(desc(FuelLog.date)).offset(skip).limit(limit).all()
    
    return logs

# ============================================================================
# UPDATE FUEL LOG
# ============================================================================

@router.put("/{log_id}", response_model=FuelLogResponse)
def update_fuel_log(
    log_id: int,
    fuel_amount: float,
    cost: Optional[float] = None,
    odometer_reading: Optional[float] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Update a fuel log entry.
    """
    log = db.query(FuelLog).filter(FuelLog.id == log_id).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fuel log with ID {log_id} not found"
        )
    
    # Get the vehicle to update fuel level
    vehicle = db.query(Vehicle).filter(Vehicle.id == log.vehicle_id).first()
    
    # Adjust vehicle fuel level (remove old amount, add new)
    vehicle.current_fuel -= log.fuel_amount
    vehicle.current_fuel += fuel_amount
    
    if vehicle.current_fuel > vehicle.fuel_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel amount would exceed tank capacity ({vehicle.fuel_capacity}L)"
        )
    
    # Update log fields
    log.fuel_amount = fuel_amount
    if cost is not None:
        log.cost = cost
    if odometer_reading is not None:
        log.odometer_reading = odometer_reading
    if notes is not None:
        log.notes = notes
    
    db.commit()
    db.refresh(log)
    
    return log

# ============================================================================
# DELETE FUEL LOG
# ============================================================================

@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fuel_log(log_id: int, db: Session = Depends(get_db)):
    """
    Delete a fuel log and adjust vehicle fuel level accordingly.
    """
    log = db.query(FuelLog).filter(FuelLog.id == log_id).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fuel log with ID {log_id} not found"
        )
    
    # Adjust vehicle fuel level
    vehicle = db.query(Vehicle).filter(Vehicle.id == log.vehicle_id).first()
    vehicle.current_fuel -= log.fuel_amount
    
    db.delete(log)
    db.commit()

# ============================================================================
# FUEL CONSUMPTION ANALYSIS
# ============================================================================

@router.get("/analytics/consumption/{vehicle_id}")
def get_fuel_consumption(
    vehicle_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Calculate fuel consumption metrics for a vehicle.
    
    Returns:
    - Total fuel consumed
    - Average consumption per day
    - Cost analysis
    - Efficiency metrics (liters per km)
    """
    # Verify vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {vehicle_id} not found"
        )
    
    # Get logs from last N days
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    logs = db.query(FuelLog).filter(
        (FuelLog.vehicle_id == vehicle_id) &
        (FuelLog.date >= cutoff_date)
    ).all()
    
    if not logs:
        return {
            "vehicle_id": vehicle_id,
            "period_days": days,
            "total_fuel_liters": 0,
            "total_cost": 0,
            "average_daily_consumption": 0,
            "efficiency_liters_per_km": 0,
            "logs_count": 0,
            "message": "No fuel logs found for this period"
        }
    
    # Calculate metrics
    total_fuel = sum(log.fuel_amount for log in logs)
    total_cost = sum(log.cost for log in logs)
    total_km = (logs[-1].odometer_reading - logs[0].odometer_reading) if len(logs) > 1 else 0
    
    avg_daily = total_fuel / days if days > 0 else 0
    liters_per_km = total_fuel / total_km if total_km > 0 else 0
    
    return {
        "vehicle_id": vehicle_id,
        "vehicle_registration": vehicle.registration,
        "period_days": days,
        "total_fuel_liters": round(total_fuel, 2),
        "total_cost": round(total_cost, 2),
        "average_daily_consumption": round(avg_daily, 2),
        "efficiency_liters_per_km": round(liters_per_km, 4),
        "total_distance_km": round(total_km, 2),
        "logs_count": len(logs),
        "date_range": {
            "from": logs[0].date.isoformat(),
            "to": logs[-1].date.isoformat()
        }
    }

# ============================================================================
# FLEET FUEL STATISTICS
# ============================================================================

@router.get("/analytics/fleet-stats")
def get_fleet_fuel_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get fuel consumption statistics for entire fleet.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all logs
    logs = db.query(FuelLog).filter(
        FuelLog.date >= cutoff_date
    ).all()
    
    if not logs:
        return {
            "period_days": days,
            "total_fuel_consumed": 0,
            "total_cost": 0,
            "average_fuel_per_log": 0,
            "logs_count": 0
        }
    
    total_fuel = sum(log.fuel_amount for log in logs)
    total_cost = sum(log.cost for log in logs)
    avg_per_log = total_fuel / len(logs) if logs else 0
    
    # Group by vehicle
    vehicle_stats = {}
    for log in logs:
        if log.vehicle_id not in vehicle_stats:
            vehicle_stats[log.vehicle_id] = {"fuel": 0, "cost": 0, "count": 0}
        vehicle_stats[log.vehicle_id]["fuel"] += log.fuel_amount
        vehicle_stats[log.vehicle_id]["cost"] += log.cost
        vehicle_stats[log.vehicle_id]["count"] += 1
    
    return {
        "period_days": days,
        "total_fuel_consumed_liters": round(total_fuel, 2),
        "total_cost": round(total_cost, 2),
        "average_fuel_per_log": round(avg_per_log, 2),
        "logs_count": len(logs),
        "vehicles_count": len(vehicle_stats),
        "by_vehicle": {
            str(v_id): {
                "fuel_liters": round(v_data["fuel"], 2),
                "cost": round(v_data["cost"], 2),
                "logs": v_data["count"]
            }
            for v_id, v_data in vehicle_stats.items()
        }
    }

# ============================================================================
# SYNC UNSYNCED LOGS
# ============================================================================

@router.get("/sync/pending")
def get_unsynced_logs(db: Session = Depends(get_db)):
    """
    Get all fuel logs that haven't been synced to cloud yet.
    Useful for offline-first mobile apps.
    """
    unsynced = db.query(FuelLog).filter(FuelLog.synced == False).all()
    
    return {
        "unsynced_count": len(unsynced),
        "logs": unsynced
    }

@router.post("/sync/mark-synced")
def mark_logs_synced(log_ids: List[int], db: Session = Depends(get_db)):
    """
    Mark fuel logs as synced after they've been sent to cloud.
    """
    logs = db.query(FuelLog).filter(FuelLog.id.in_(log_ids)).all()
    
    if not logs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No logs found with provided IDs"
        )
    
    for log in logs:
        log.synced = True
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Marked {len(logs)} logs as synced"
    }
