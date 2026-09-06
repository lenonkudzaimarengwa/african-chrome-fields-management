"""
Ore Load Management API Routes
Handles chrome ore loading, tracking, and transportation
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import OreLoad, Vehicle, Worker
from app.schemas import OreLoadCreate, OreLoadUpdate, OreLoadResponse

router = APIRouter()

# ============================================================================
# CREATE ORE LOAD
# ============================================================================

@router.post("/", response_model=OreLoadResponse, status_code=status.HTTP_201_CREATED)
def create_ore_load(ore_load: OreLoadCreate, db: Session = Depends(get_db)):
    """
    Create a new ore load (truck shipment of chrome ore).
    
    - **load_number**: Unique load identifier
    - **vehicle_id**: ID of the truck carrying the ore
    - **weight_kg**: Total weight of ore in kilograms
    - **ore_grade**: Grade/quality of ore (Premium, Standard, etc.)
    - **origin_pit**: Which pit the ore came from
    - **destination**: Where the ore is going (processing plant, storage)
    - **driver_id**: ID of the driver
    """
    # Verify vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == ore_load.vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {ore_load.vehicle_id} not found"
        )
    
    # Verify driver exists
    driver = db.query(Worker).filter(Worker.id == ore_load.driver_id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver with ID {ore_load.driver_id} not found"
        )
    
    # Check if load number already exists
    existing = db.query(OreLoad).filter(OreLoad.load_number == ore_load.load_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Load with number '{ore_load.load_number}' already exists"
        )
    
    db_load = OreLoad(**ore_load.dict())
    db.add(db_load)
    db.commit()
    db.refresh(db_load)
    
    return db_load

# ============================================================================
# GET ALL ORE LOADS
# ============================================================================

@router.get("/", response_model=List[OreLoadResponse])
def get_ore_loads(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    vehicle_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    ore_grade: Optional[str] = None,
    unloaded_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all ore loads with pagination and optional filtering.
    
    - **skip**: Number of records to skip
    - **limit**: Maximum records to return
    - **vehicle_id**: Filter by vehicle
    - **driver_id**: Filter by driver
    - **ore_grade**: Filter by ore grade
    - **unloaded_only**: Show only unloaded shipments
    """
    query = db.query(OreLoad)
    
    if vehicle_id:
        query = query.filter(OreLoad.vehicle_id == vehicle_id)
    if driver_id:
        query = query.filter(OreLoad.driver_id == driver_id)
    if ore_grade:
        query = query.filter(OreLoad.ore_grade == ore_grade)
    if unloaded_only:
        query = query.filter(OreLoad.unloaded_at == None)
    
    loads = query.order_by(desc(OreLoad.loaded_at)).offset(skip).limit(limit).all()
    return loads

# ============================================================================
# GET ORE LOAD BY ID
# ============================================================================

@router.get("/{load_id}", response_model=OreLoadResponse)
def get_ore_load(load_id: int, db: Session = Depends(get_db)):
    """
    Get a specific ore load by ID.
    """
    load = db.query(OreLoad).filter(OreLoad.id == load_id).first()
    
    if not load:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ore load with ID {load_id} not found"
        )
    
    return load

# ============================================================================
# GET ORE LOAD BY LOAD_NUMBER
# ============================================================================

@router.get("/search/{load_number}")
def search_ore_load(load_number: str, db: Session = Depends(get_db)):
    """
    Search for ore load by load number.
    """
    load = db.query(OreLoad).filter(OreLoad.load_number == load_number).first()
    
    if not load:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ore load '{load_number}' not found"
        )
    
    return load

# ============================================================================
# UPDATE ORE LOAD
# ============================================================================

@router.put("/{load_id}", response_model=OreLoadResponse)
def update_ore_load(
    load_id: int,
    ore_load_update: OreLoadUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an ore load (mark as unloaded, add notes).
    """
    db_load = db.query(OreLoad).filter(OreLoad.id == load_id).first()
    
    if not db_load:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ore load with ID {load_id} not found"
        )
    
    update_data = ore_load_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_load, field, value)
    
    db.commit()
    db.refresh(db_load)
    
    return db_load

# ============================================================================
# MARK LOAD AS UNLOADED
# ============================================================================

@router.patch("/{load_id}/unload", response_model=OreLoadResponse)
def mark_load_unloaded(load_id: int, db: Session = Depends(get_db)):
    """
    Mark an ore load as unloaded (complete delivery).
    """
    load = db.query(OreLoad).filter(OreLoad.id == load_id).first()
    
    if not load:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ore load with ID {load_id} not found"
        )
    
    if load.unloaded_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Load is already marked as unloaded"
        )
    
    load.unloaded_at = datetime.utcnow()
    db.commit()
    db.refresh(load)
    
    return load

# ============================================================================
# DELETE ORE LOAD
# ============================================================================

@router.delete("/{load_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ore_load(load_id: int, db: Session = Depends(get_db)):
    """
    Delete an ore load record.
    """
    load = db.query(OreLoad).filter(OreLoad.id == load_id).first()
    
    if not load:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ore load with ID {load_id} not found"
        )
    
    db.delete(load)
    db.commit()

# ============================================================================
# ORE LOAD STATISTICS
# ============================================================================

@router.get("/stats/summary")
def get_ore_load_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get ore loading statistics for the last N days.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    loads = db.query(OreLoad).filter(OreLoad.loaded_at >= cutoff_date).all()
    
    if not loads:
        return {
            "period_days": days,
            "total_loads": 0,
            "completed_loads": 0,
            "total_ore_kg": 0,
            "message": "No loads found for this period"
        }
    
    total_ore = sum(load.weight_kg for load in loads)
    completed = sum(1 for load in loads if load.unloaded_at)
    
    # Grade distribution
    grades = {}
    for load in loads:
        grades[load.ore_grade] = grades.get(load.ore_grade, 0) + load.weight_kg
    
    # Destination distribution
    destinations = {}
    for load in loads:
        destinations[load.destination] = destinations.get(load.destination, 0) + 1
    
    return {
        "period_days": days,
        "total_loads": len(loads),
        "completed_loads": completed,
        "pending_loads": len(loads) - completed,
        "total_ore_kg": round(total_ore, 2),
        "average_load_kg": round(total_ore / len(loads), 2) if loads else 0,
        "by_grade": {g: round(w, 2) for g, w in grades.items()},
        "by_destination": destinations,
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# GET LOADS BY DATE RANGE
# ============================================================================

@router.get("/range/by-date")
def get_loads_by_date_range(
    start_date: str,  # ISO format: 2024-01-01
    end_date: str,    # ISO format: 2024-01-31
    db: Session = Depends(get_db)
):
    """
    Get ore loads within a specific date range.
    """
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format: YYYY-MM-DD"
        )
    
    loads = db.query(OreLoad).filter(
        (OreLoad.loaded_at >= start) &
        (OreLoad.loaded_at <= end)
    ).order_by(desc(OreLoad.loaded_at)).all()
    
    return {
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat()
        },
        "total_loads": len(loads),
        "total_ore_kg": round(sum(l.weight_kg for l in loads), 2),
        "loads": loads
    }

# ============================================================================
# GET LOADS BY DESTINATION
# ============================================================================

@router.get("/destination/{destination}")
def get_loads_by_destination(
    destination: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all ore loads destined for a specific location.
    """
    loads = db.query(OreLoad).filter(
        OreLoad.destination == destination
    ).order_by(desc(OreLoad.loaded_at)).offset(skip).limit(limit).all()
    
    return {
        "destination": destination,
        "count": len(loads),
        "loads": loads
    }

# ============================================================================
# GET LOADS BY PIT
# ============================================================================

@router.get("/pit/{pit_name}")
def get_loads_by_pit(
    pit_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all ore loads from a specific pit/mining location.
    """
    loads = db.query(OreLoad).filter(
        OreLoad.origin_pit == pit_name
    ).order_by(desc(OreLoad.loaded_at)).offset(skip).limit(limit).all()
    
    return {
        "origin_pit": pit_name,
        "count": len(loads),
        "total_ore_kg": round(sum(l.weight_kg for l in loads), 2),
        "loads": loads
    }

# ============================================================================
# ACTIVE LOADS (NOT YET UNLOADED)
# ============================================================================

@router.get("/status/active")
def get_active_loads(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all active loads (not yet unloaded).
    """
    loads = db.query(OreLoad).filter(
        OreLoad.unloaded_at == None
    ).order_by(desc(OreLoad.loaded_at)).offset(skip).limit(limit).all()
    
    return {
        "active_loads": len(loads),
        "total_ore_in_transit_kg": round(sum(l.weight_kg for l in loads), 2),
        "loads": loads
    }

# ============================================================================
# DRIVER PERFORMANCE METRICS
# ============================================================================

@router.get("/driver/{driver_id}/metrics")
def get_driver_metrics(
    driver_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get ore loading metrics for a specific driver.
    """
    # Verify driver exists
    driver = db.query(Worker).filter(Worker.id == driver_id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver with ID {driver_id} not found"
        )
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    loads = db.query(OreLoad).filter(
        (OreLoad.driver_id == driver_id) &
        (OreLoad.loaded_at >= cutoff_date)
    ).all()
    
    if not loads:
        return {
            "driver_id": driver_id,
            "driver_name": f"{driver.first_name} {driver.last_name}",
            "period_days": days,
            "total_loads": 0,
            "message": "No loads found"
        }
    
    completed_loads = [l for l in loads if l.unloaded_at]
    total_ore = sum(l.weight_kg for l in loads)
    
    return {
        "driver_id": driver_id,
        "driver_name": f"{driver.first_name} {driver.last_name}",
        "period_days": days,
        "total_loads": len(loads),
        "completed_loads": len(completed_loads),
        "total_ore_transported_kg": round(total_ore, 2),
        "average_load_kg": round(total_ore / len(loads), 2) if loads else 0,
        "completion_rate_percent": round((len(completed_loads) / len(loads) * 100), 2) if loads else 0
    }

# ============================================================================
# VEHICLE UTILIZATION
# ============================================================================

@router.get("/vehicle/{vehicle_id}/utilization")
def get_vehicle_utilization(
    vehicle_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get ore transportation metrics for a specific vehicle.
    """
    # Verify vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {vehicle_id} not found"
        )
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    loads = db.query(OreLoad).filter(
        (OreLoad.vehicle_id == vehicle_id) &
        (OreLoad.loaded_at >= cutoff_date)
    ).all()
    
    if not loads:
        return {
            "vehicle_id": vehicle_id,
            "vehicle_registration": vehicle.registration,
            "period_days": days,
            "total_loads": 0,
            "message": "No loads found"
        }
    
    total_ore = sum(l.weight_kg for l in loads)
    completed = len([l for l in loads if l.unloaded_at])
    
    return {
        "vehicle_id": vehicle_id,
        "vehicle_registration": vehicle.registration,
        "vehicle_type": vehicle.vehicle_type,
        "period_days": days,
        "total_loads": len(loads),
        "completed_deliveries": completed,
        "total_ore_transported_kg": round(total_ore, 2),
        "average_load_weight_kg": round(total_ore / len(loads), 2),
        "utilization_rate_percent": round((completed / len(loads) * 100), 2) if loads else 0
    }

# ============================================================================
# SYNC UNSYNCED LOADS
# ============================================================================

@router.get("/sync/pending")
def get_unsynced_loads(db: Session = Depends(get_db)):
    """
    Get all ore loads that haven't been synced (offline support).
    """
    unsynced = db.query(OreLoad).filter(OreLoad.synced == False).all()
    
    return {
        "unsynced_count": len(unsynced),
        "loads": unsynced
    }

@router.post("/sync/mark-synced")
def mark_loads_synced(load_ids: List[int], db: Session = Depends(get_db)):
    """
    Mark ore loads as synced after cloud upload.
    """
    loads = db.query(OreLoad).filter(OreLoad.id.in_(load_ids)).all()
    
    if not loads:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No loads found with provided IDs"
        )
    
    for load in loads:
        load.synced = True
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Marked {len(loads)} loads as synced"
    }
