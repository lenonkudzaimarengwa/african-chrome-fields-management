"""
Equipment Management API Routes
Handles all mining equipment tracking, maintenance, and inspection
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Equipment, EquipmentInspection, MaintenanceLog
from app.schemas import (
    EquipmentCreate, EquipmentUpdate, EquipmentResponse,
    EquipmentInspectionCreate, EquipmentInspectionResponse,
    MaintenanceLogCreate, MaintenanceLogResponse, EquipmentStatusSchema
)

router = APIRouter()

# ============================================================================
# EQUIPMENT MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
def create_equipment(equipment: EquipmentCreate, db: Session = Depends(get_db)):
    """
    Create a new piece of equipment.
    
    - **equipment_id**: Unique identifier (e.g., "EXCAVATOR-001")
    - **equipment_type**: Type (Excavator, Loader, Dozer, Drill, etc.)
    - **make**: Manufacturer
    - **model**: Model name
    - **location**: Current location/pit
    """
    # Check if equipment already exists
    existing = db.query(Equipment).filter(Equipment.equipment_id == equipment.equipment_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Equipment with ID '{equipment.equipment_id}' already exists"
        )
    
    db_equipment = Equipment(**equipment.dict())
    db.add(db_equipment)
    db.commit()
    db.refresh(db_equipment)
    
    return db_equipment

@router.get("/", response_model=List[EquipmentResponse])
def get_equipment(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    equipment_type: Optional[str] = None,
    status_filter: Optional[EquipmentStatusSchema] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all equipment with pagination and optional filtering.
    
    - **equipment_type**: Filter by type
    - **status_filter**: Filter by status (working, idle, maintenance, broken)
    - **location**: Filter by location/pit
    """
    query = db.query(Equipment)
    
    if equipment_type:
        query = query.filter(Equipment.equipment_type == equipment_type)
    if status_filter:
        query = query.filter(Equipment.status == status_filter)
    if location:
        query = query.filter(Equipment.location == location)
    
    equipment = query.offset(skip).limit(limit).all()
    return equipment

@router.get("/{equipment_id}", response_model=EquipmentResponse)
def get_equipment_by_id(equipment_id: int, db: Session = Depends(get_db)):
    """Get a specific piece of equipment by ID."""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with ID {equipment_id} not found"
        )
    
    return equipment

@router.get("/search/{equipment_identifier}")
def search_equipment(equipment_identifier: str, db: Session = Depends(get_db)):
    """Search for equipment by equipment_id."""
    equipment = db.query(Equipment).filter(Equipment.equipment_id == equipment_identifier).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment '{equipment_identifier}' not found"
        )
    
    return equipment

@router.put("/{equipment_id}", response_model=EquipmentResponse)
def update_equipment(
    equipment_id: int,
    equipment_update: EquipmentUpdate,
    db: Session = Depends(get_db)
):
    """Update equipment information."""
    db_equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not db_equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with ID {equipment_id} not found"
        )
    
    update_data = equipment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_equipment, field, value)
    
    db.commit()
    db.refresh(db_equipment)
    
    return db_equipment

@router.patch("/{equipment_id}/status", response_model=EquipmentResponse)
def update_equipment_status(
    equipment_id: int,
    new_status: EquipmentStatusSchema,
    db: Session = Depends(get_db)
):
    """Update equipment status (working, idle, maintenance, broken)."""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with ID {equipment_id} not found"
        )
    
    equipment.status = new_status
    db.commit()
    db.refresh(equipment)
    
    return equipment

@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment(equipment_id: int, db: Session = Depends(get_db)):
    """Delete equipment record."""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with ID {equipment_id} not found"
        )
    
    db.delete(equipment)
    db.commit()

# ============================================================================
# EQUIPMENT STATISTICS
# ============================================================================

@router.get("/stats/summary")
def get_equipment_stats(db: Session = Depends(get_db)):
    """Get equipment fleet statistics."""
    total = db.query(Equipment).count()
    working = db.query(Equipment).filter(Equipment.status == "working").count()
    idle = db.query(Equipment).filter(Equipment.status == "idle").count()
    maintenance = db.query(Equipment).filter(Equipment.status == "maintenance").count()
    broken = db.query(Equipment).filter(Equipment.status == "broken").count()
    
    # Get type distribution
    types = {}
    for eq_type in db.query(Equipment.equipment_type, func.count(Equipment.id)).group_by(Equipment.equipment_type).all():
        types[eq_type[0]] = eq_type[1]
    
    return {
        "total_equipment": total,
        "working": working,
        "idle": idle,
        "maintenance": maintenance,
        "broken": broken,
        "by_type": types,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/status/working")
def get_working_equipment(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all equipment currently working."""
    equipment = db.query(Equipment).filter(
        Equipment.status == "working"
    ).offset(skip).limit(limit).all()
    
    return {
        "working_count": len(equipment),
        "equipment": equipment
    }

@router.get("/status/broken")
def get_broken_equipment(db: Session = Depends(get_db)):
    """Get all equipment that is broken (needs urgent attention)."""
    equipment = db.query(Equipment).filter(Equipment.status == "broken").all()
    
    return {
        "broken_count": len(equipment),
        "equipment": equipment
    }

@router.get("/maintenance-due")
def get_maintenance_due(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get equipment with maintenance due in next N days."""
    cutoff = datetime.utcnow() + timedelta(days=days)
    
    equipment = db.query(Equipment).filter(
        (Equipment.next_maintenance != None) &
        (Equipment.next_maintenance <= cutoff)
    ).all()
    
    return {
        "days_ahead": days,
        "maintenance_due_count": len(equipment),
        "equipment": equipment
    }

# ============================================================================
# EQUIPMENT INSPECTION ENDPOINTS
# ============================================================================

@router.post("/{equipment_id}/inspections", response_model=EquipmentInspectionResponse, status_code=status.HTTP_201_CREATED)
def create_inspection(
    equipment_id: int,
    inspection: EquipmentInspectionCreate,
    db: Session = Depends(get_db)
):
    """Create an equipment inspection record."""
    # Verify equipment exists
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with ID {equipment_id} not found"
        )
    
    # Update inspection with equipment_id
    inspection_data = inspection.dict()
    inspection_data['equipment_id'] = equipment_id
    
    db_inspection = EquipmentInspection(**inspection_data)
    db.add(db_inspection)
    db.commit()
    db.refresh(db_inspection)
    
    return db_inspection

@router.get("/{equipment_id}/inspections", response_model=List[EquipmentInspectionResponse])
def get_equipment_inspections(
    equipment_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all inspections for a specific equipment."""
    inspections = db.query(EquipmentInspection).filter(
        EquipmentInspection.equipment_id == equipment_id
    ).order_by(desc(EquipmentInspection.checked_at)).offset(skip).limit(limit).all()
    
    return inspections

@router.get("/inspections/recent")
def get_recent_inspections(
    days: int = Query(7, ge=1, le=30),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get recent inspections from last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    inspections = db.query(EquipmentInspection).filter(
        EquipmentInspection.checked_at >= cutoff
    ).order_by(desc(EquipmentInspection.checked_at)).offset(skip).limit(limit).all()
    
    return inspections

# ============================================================================
# MAINTENANCE LOG ENDPOINTS
# ============================================================================

@router.post("/{equipment_id}/maintenance", response_model=MaintenanceLogResponse, status_code=status.HTTP_201_CREATED)
def create_maintenance_log(
    equipment_id: int,
    maintenance: MaintenanceLogCreate,
    db: Session = Depends(get_db)
):
    """Record equipment maintenance."""
    # Verify equipment exists
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with ID {equipment_id} not found"
        )
    
    # Update maintenance with equipment_id
    maintenance_data = maintenance.dict()
    maintenance_data['equipment_id'] = equipment_id
    
    db_maintenance = MaintenanceLog(**maintenance_data)
    db.add(db_maintenance)
    
    # Update equipment's last maintenance
    equipment.last_maintenance = datetime.utcnow()
    
    db.commit()
    db.refresh(db_maintenance)
    
    return db_maintenance

@router.get("/{equipment_id}/maintenance", response_model=List[MaintenanceLogResponse])
def get_equipment_maintenance_history(
    equipment_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get maintenance history for equipment."""
    logs = db.query(MaintenanceLog).filter(
        MaintenanceLog.equipment_id == equipment_id
    ).order_by(desc(MaintenanceLog.maintenance_date)).offset(skip).limit(limit).all()
    
    return logs

@router.get("/maintenance/all")
def get_all_maintenance_logs(
    days: int = Query(30, ge=1, le=365),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all maintenance logs from last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    logs = db.query(MaintenanceLog).filter(
        MaintenanceLog.maintenance_date >= cutoff
    ).order_by(desc(MaintenanceLog.maintenance_date)).offset(skip).limit(limit).all()
    
    return logs

@router.get("/maintenance/stats")
def get_maintenance_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get maintenance statistics."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    logs = db.query(MaintenanceLog).filter(
        MaintenanceLog.maintenance_date >= cutoff
    ).all()
    
    total_cost = sum(log.cost for log in logs)
    
    # Group by maintenance type
    types = {}
    for log in logs:
        types[log.maintenance_type] = types.get(log.maintenance_type, 0) + 1
    
    return {
        "period_days": days,
        "total_maintenance_events": len(logs),
        "total_maintenance_cost": round(total_cost, 2),
        "average_cost_per_event": round(total_cost / len(logs), 2) if logs else 0,
        "by_type": types,
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# EQUIPMENT BY LOCATION
# ============================================================================

@router.get("/location/{location}")
def get_equipment_by_location(
    location: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all equipment at a specific location/pit."""
    equipment = db.query(Equipment).filter(
        Equipment.location == location
    ).offset(skip).limit(limit).all()
    
    return {
        "location": location,
        "count": len(equipment),
        "equipment": equipment
    }

# ============================================================================
# EQUIPMENT DOWNTIME ANALYSIS
# ============================================================================

@router.get("/{equipment_id}/downtime")
def get_equipment_downtime(
    equipment_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Analyze equipment downtime from maintenance records."""
    # Verify equipment exists
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with ID {equipment_id} not found"
        )
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    logs = db.query(MaintenanceLog).filter(
        (MaintenanceLog.equipment_id == equipment_id) &
        (MaintenanceLog.maintenance_date >= cutoff)
    ).all()
    
    if not logs:
        return {
            "equipment_id": equipment_id,
            "period_days": days,
            "total_downtime_events": 0,
            "message": "No downtime data"
        }
    
    return {
        "equipment_id": equipment_id,
        "equipment_type": equipment.equipment_type,
        "period_days": days,
        "total_maintenance_events": len(logs),
        "total_maintenance_cost": round(sum(log.cost for log in logs), 2),
        "maintenance_types": list(set(log.maintenance_type for log in logs)),
        "average_days_between_maintenance": round(days / len(logs), 1) if logs else 0
    }

# ============================================================================
# SYNC ENDPOINTS (Offline Support)
# ============================================================================

@router.get("/sync/pending")
def get_unsynced_equipment_data(db: Session = Depends(get_db)):
    """Get unsynced equipment-related data."""
    unsynced_inspections = db.query(EquipmentInspection).filter(EquipmentInspection.synced == False).all()
    unsynced_maintenance = db.query(MaintenanceLog).all()  # Maintenance doesn't have synced field
    
    return {
        "unsynced_inspections": len(unsynced_inspections),
        "inspections": unsynced_inspections,
        "maintenance_logs": unsynced_maintenance
    }

@router.post("/sync/mark-synced")
def mark_inspections_synced(inspection_ids: List[int], db: Session = Depends(get_db)):
    """Mark inspections as synced."""
    inspections = db.query(EquipmentInspection).filter(EquipmentInspection.id.in_(inspection_ids)).all()
    
    if not inspections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No inspections found"
        )
    
    for inspection in inspections:
        inspection.synced = True
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Marked {len(inspections)} inspections as synced"
    }
