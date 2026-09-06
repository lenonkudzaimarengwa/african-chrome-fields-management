"""
Vehicle Management API Routes
Handles all vehicle/truck-related endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import Vehicle
from app.schemas import VehicleCreate, VehicleUpdate, VehicleResponse, VehicleStatusSchema

router = APIRouter()

# ============================================================================
# CREATE VEHICLE
# ============================================================================

@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(vehicle: VehicleCreate, db: Session = Depends(get_db)):
    """
    Create a new vehicle.
    
    - **vehicle_id**: Unique vehicle identifier (e.g., "TRUCK-001")
    - **vehicle_type**: Type of vehicle (Haulage Truck, Excavator, Loader, etc.)
    - **make**: Manufacturer (Volvo, Caterpillar, etc.)
    - **model**: Model name
    - **year**: Manufacturing year
    - **registration**: License plate/registration number
    - **fuel_capacity**: Tank capacity in liters
    """
    # Check if vehicle already exists
    existing = db.query(Vehicle).filter(
        (Vehicle.vehicle_id == vehicle.vehicle_id) | 
        (Vehicle.registration == vehicle.registration)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle with this ID or registration already exists"
        )
    
    db_vehicle = Vehicle(**vehicle.dict())
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    
    return db_vehicle

# ============================================================================
# GET ALL VEHICLES
# ============================================================================

@router.get("/", response_model=List[VehicleResponse])
def get_vehicles(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[VehicleStatusSchema] = None,
    db: Session = Depends(get_db)
):
    """
    Get all vehicles with pagination and optional filtering.
    
    - **skip**: Number of records to skip
    - **limit**: Number of records to return (max 100)
    - **status_filter**: Filter by vehicle status (optional)
    """
    query = db.query(Vehicle)
    
    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    
    vehicles = query.offset(skip).limit(limit).all()
    return vehicles

# ============================================================================
# GET VEHICLE BY ID
# ============================================================================

@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    """
    Get a specific vehicle by ID.
    Returns 404 if vehicle not found.
    """
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {vehicle_id} not found"
        )
    
    return vehicle

# ============================================================================
# GET VEHICLE BY VEHICLE_ID (Registration Number)
# ============================================================================

@router.get("/search/{vehicle_identifier}")
def search_vehicle(vehicle_identifier: str, db: Session = Depends(get_db)):
    """
    Search for vehicle by vehicle_id or registration number.
    """
    vehicle = db.query(Vehicle).filter(
        (Vehicle.vehicle_id == vehicle_identifier) | 
        (Vehicle.registration == vehicle_identifier)
    ).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle '{vehicle_identifier}' not found"
        )
    
    return vehicle

# ============================================================================
# UPDATE VEHICLE
# ============================================================================

@router.put("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: int,
    vehicle_update: VehicleUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a vehicle's information.
    Only provided fields will be updated.
    """
    db_vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    
    if not db_vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {vehicle_id} not found"
        )
    
    # Update only provided fields
    update_data = vehicle_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_vehicle, field, value)
    
    db_vehicle.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_vehicle)
    
    return db_vehicle

# ============================================================================
# UPDATE VEHICLE FUEL LEVEL
# ============================================================================

@router.patch("/{vehicle_id}/fuel", response_model=VehicleResponse)
def update_fuel_level(
    vehicle_id: int,
    fuel_level: float,
    db: Session = Depends(get_db)
):
    """
    Update only the fuel level for a vehicle.
    """
    if fuel_level < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fuel level cannot be negative"
        )
    
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {vehicle_id} not found"
        )
    
    if fuel_level > vehicle.fuel_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fuel level exceeds capacity ({vehicle.fuel_capacity}L)"
        )
    
    vehicle.current_fuel = fuel_level
    vehicle.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(vehicle)
    
    return vehicle

# ============================================================================
# UPDATE VEHICLE STATUS
# ============================================================================

@router.patch("/{vehicle_id}/status", response_model=VehicleResponse)
def update_vehicle_status(
    vehicle_id: int,
    new_status: VehicleStatusSchema,
    db: Session = Depends(get_db)
):
    """
    Update vehicle status (operational, maintenance, out_of_service).
    """
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {vehicle_id} not found"
        )
    
    vehicle.status = new_status
    vehicle.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(vehicle)
    
    return vehicle

# ============================================================================
# DELETE VEHICLE
# ============================================================================

@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    """
    Delete a vehicle. This will cascade delete related fuel logs.
    WARNING: This is a hard delete and cannot be undone.
    """
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {vehicle_id} not found"
        )
    
    db.delete(vehicle)
    db.commit()

# ============================================================================
# GET VEHICLE STATISTICS
# ============================================================================

@router.get("/stats/summary", response_model=dict)
def get_vehicle_stats(db: Session = Depends(get_db)):
    """
    Get summary statistics about all vehicles.
    """
    total_vehicles = db.query(Vehicle).count()
    operational = db.query(Vehicle).filter(Vehicle.status == "operational").count()
    maintenance = db.query(Vehicle).filter(Vehicle.status == "maintenance").count()
    out_of_service = db.query(Vehicle).filter(Vehicle.status == "out_of_service").count()
    
    # Calculate average fuel consumption
    avg_fuel = db.query(Vehicle).with_entities(
        Vehicle.current_fuel.avg()
    ).scalar() or 0
    
    return {
        "total_vehicles": total_vehicles,
        "operational": operational,
        "maintenance": maintenance,
        "out_of_service": out_of_service,
        "average_fuel_level": round(avg_fuel, 2),
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# GET LOW FUEL VEHICLES
# ============================================================================

@router.get("/alerts/low-fuel", response_model=List[VehicleResponse])
def get_low_fuel_vehicles(
    threshold_percent: int = Query(20, ge=0, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all vehicles with fuel below a certain threshold percentage.
    Default threshold is 20% of tank capacity.
    """
    vehicles = db.query(Vehicle).all()
    
    low_fuel_vehicles = [
        v for v in vehicles 
        if (v.current_fuel / v.fuel_capacity * 100) < threshold_percent
    ]
    
    return low_fuel_vehicles

# ============================================================================
# BULK OPERATIONS
# ============================================================================

@router.post("/bulk/status-update")
def bulk_update_status(
    vehicle_ids: List[int],
    new_status: VehicleStatusSchema,
    db: Session = Depends(get_db)
):
    """
    Update status for multiple vehicles at once.
    """
    vehicles = db.query(Vehicle).filter(Vehicle.id.in_(vehicle_ids)).all()
    
    if not vehicles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No vehicles found with provided IDs"
        )
    
    for vehicle in vehicles:
        vehicle.status = new_status
        vehicle.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Updated status for {len(vehicles)} vehicles",
        "updated_count": len(vehicles)
    }
