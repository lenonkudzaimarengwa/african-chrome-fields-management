"""
Shift Management API Routes
Handles worker shifts, time tracking, and attendance
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import ShiftLog, Worker
from app.schemas import ShiftLogCreate, ShiftLogUpdate, ShiftLogResponse

router = APIRouter()

# ============================================================================
# CREATE SHIFT LOG
# ============================================================================

@router.post("/", response_model=ShiftLogResponse, status_code=status.HTTP_201_CREATED)
def create_shift_log(shift: ShiftLogCreate, db: Session = Depends(get_db)):
    """
    Create a new shift log (clock in).
    
    - **worker_id**: ID of the worker
    - **shift_type**: Type of shift (morning, afternoon, night)
    - **date**: Date of the shift
    - **clock_in**: Clock-in time
    """
    # Verify worker exists
    worker = db.query(Worker).filter(Worker.id == shift.worker_id).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {shift.worker_id} not found"
        )
    
    db_shift = ShiftLog(**shift.dict())
    db.add(db_shift)
    db.commit()
    db.refresh(db_shift)
    
    return db_shift

# ============================================================================
# GET ALL SHIFTS
# ============================================================================

@router.get("/", response_model=List[ShiftLogResponse])
def get_shifts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    worker_id: Optional[int] = None,
    shift_type: Optional[str] = None,
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all shift logs with pagination and filtering.
    
    - **worker_id**: Filter by worker
    - **shift_type**: Filter by shift type (morning, afternoon, night)
    - **date**: Filter by date (ISO format: 2024-01-01)
    """
    query = db.query(ShiftLog)
    
    if worker_id:
        query = query.filter(ShiftLog.worker_id == worker_id)
    if shift_type:
        query = query.filter(ShiftLog.shift_type == shift_type)
    if date:
        try:
            shift_date = datetime.fromisoformat(date).date()
            query = query.filter(ShiftLog.date == shift_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use ISO format: YYYY-MM-DD"
            )
    
    shifts = query.order_by(desc(ShiftLog.date)).offset(skip).limit(limit).all()
    return shifts

# ============================================================================
# GET SHIFT BY ID
# ============================================================================

@router.get("/{shift_id}", response_model=ShiftLogResponse)
def get_shift(shift_id: int, db: Session = Depends(get_db)):
    """Get a specific shift log by ID."""
    shift = db.query(ShiftLog).filter(ShiftLog.id == shift_id).first()
    
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with ID {shift_id} not found"
        )
    
    return shift

# ============================================================================
# CLOCK OUT (UPDATE SHIFT)
# ============================================================================

@router.patch("/{shift_id}/clock-out", response_model=ShiftLogResponse)
def clock_out(
    shift_id: int,
    clock_out_time: Optional[datetime] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Clock out a worker (end shift).
    """
    shift = db.query(ShiftLog).filter(ShiftLog.id == shift_id).first()
    
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with ID {shift_id} not found"
        )
    
    if shift.clock_out:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This shift is already clocked out"
        )
    
    shift.clock_out = clock_out_time or datetime.utcnow()
    if notes:
        shift.notes = notes
    shift.status = "completed"
    
    db.commit()
    db.refresh(shift)
    
    return shift

# ============================================================================
# UPDATE SHIFT
# ============================================================================

@router.put("/{shift_id}", response_model=ShiftLogResponse)
def update_shift(
    shift_id: int,
    shift_update: ShiftLogUpdate,
    db: Session = Depends(get_db)
):
    """Update shift information."""
    db_shift = db.query(ShiftLog).filter(ShiftLog.id == shift_id).first()
    
    if not db_shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with ID {shift_id} not found"
        )
    
    update_data = shift_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_shift, field, value)
    
    db.commit()
    db.refresh(db_shift)
    
    return db_shift

# ============================================================================
# DELETE SHIFT
# ============================================================================

@router.delete("/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    """Delete a shift log."""
    shift = db.query(ShiftLog).filter(ShiftLog.id == shift_id).first()
    
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shift with ID {shift_id} not found"
        )
    
    db.delete(shift)
    db.commit()

# ============================================================================
# ACTIVE SHIFTS (CURRENTLY CLOCKED IN)
# ============================================================================

@router.get("/status/active")
def get_active_shifts(db: Session = Depends(get_db)):
    """Get all workers currently clocked in (active shifts)."""
    active_shifts = db.query(ShiftLog).filter(
        ShiftLog.clock_out == None
    ).all()
    
    return {
        "active_count": len(active_shifts),
        "shifts": active_shifts
    }

# ============================================================================
# TODAY'S SHIFTS
# ============================================================================

@router.get("/today/all")
def get_todays_shifts(db: Session = Depends(get_db)):
    """Get all shifts for today."""
    today = datetime.utcnow().date()
    
    shifts = db.query(ShiftLog).filter(ShiftLog.date == today).all()
    
    active = [s for s in shifts if s.clock_out is None]
    completed = [s for s in shifts if s.clock_out is not None]
    
    return {
        "date": today.isoformat(),
        "total_shifts": len(shifts),
        "active": len(active),
        "completed": len(completed),
        "active_shifts": active,
        "completed_shifts": completed
    }

# ============================================================================
# WORKER SHIFT HISTORY
# ============================================================================

@router.get("/worker/{worker_id}/history")
def get_worker_shift_history(
    worker_id: int,
    days: int = Query(30, ge=1, le=365),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get shift history for a specific worker.
    """
    # Verify worker exists
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {worker_id} not found"
        )
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    shifts = db.query(ShiftLog).filter(
        (ShiftLog.worker_id == worker_id) &
        (ShiftLog.date >= cutoff_date)
    ).order_by(desc(ShiftLog.date)).offset(skip).limit(limit).all()
    
    return {
        "worker_id": worker_id,
        "worker_name": f"{worker.first_name} {worker.last_name}",
        "period_days": days,
        "total_shifts": len(shifts),
        "shifts": shifts
    }

# ============================================================================
# WORKER HOURS CALCULATION
# ============================================================================

@router.get("/worker/{worker_id}/hours")
def calculate_worker_hours(
    worker_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Calculate total hours worked by a worker in the last N days.
    """
    # Verify worker exists
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {worker_id} not found"
        )
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    shifts = db.query(ShiftLog).filter(
        (ShiftLog.worker_id == worker_id) &
        (ShiftLog.date >= cutoff_date) &
        (ShiftLog.clock_out != None)
    ).all()
    
    total_hours = 0
    for shift in shifts:
        if shift.clock_out and shift.clock_in:
            hours = (shift.clock_out - shift.clock_in).total_seconds() / 3600
            total_hours += hours
    
    return {
        "worker_id": worker_id,
        "worker_name": f"{worker.first_name} {worker.last_name}",
        "period_days": days,
        "total_completed_shifts": len(shifts),
        "total_hours_worked": round(total_hours, 2),
        "average_shift_hours": round(total_hours / len(shifts), 2) if shifts else 0
    }

# ============================================================================
# SHIFT STATISTICS
# ============================================================================

@router.get("/stats/summary")
def get_shift_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get shift statistics for the last N days."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    shifts = db.query(ShiftLog).filter(ShiftLog.date >= cutoff_date).all()
    
    if not shifts:
        return {
            "period_days": days,
            "total_shifts": 0,
            "message": "No shifts found"
        }
    
    completed = [s for s in shifts if s.clock_out]
    active = [s for s in shifts if not s.clock_out]
    
    total_hours = 0
    for shift in completed:
        if shift.clock_in and shift.clock_out:
            hours = (shift.clock_out - shift.clock_in).total_seconds() / 3600
            total_hours += hours
    
    # Shift type distribution
    shift_types = {}
    for shift in shifts:
        shift_types[shift.shift_type] = shift_types.get(shift.shift_type, 0) + 1
    
    # Workers who worked
    workers_count = db.query(func.count(func.distinct(ShiftLog.worker_id))).filter(
        ShiftLog.date >= cutoff_date
    ).scalar()
    
    return {
        "period_days": days,
        "total_shifts": len(shifts),
        "completed_shifts": len(completed),
        "active_shifts": len(active),
        "unique_workers": workers_count,
        "total_hours_worked": round(total_hours, 2),
        "average_hours_per_shift": round(total_hours / len(completed), 2) if completed else 0,
        "by_shift_type": shift_types,
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# ABSENT WORKERS (TODAY)
# ============================================================================

@router.get("/today/absent")
def get_absent_workers(db: Session = Depends(get_db)):
    """
    Get workers who are supposed to be working but haven't clocked in today.
    """
    today = datetime.utcnow().date()
    
    # Get all active workers
    active_workers = db.query(Worker).filter(Worker.status == "active").all()
    
    # Get workers who have shifts today
    workers_with_shifts = db.query(ShiftLog.worker_id).filter(
        ShiftLog.date == today
    ).distinct().all()
    
    workers_with_shifts_ids = [w[0] for w in workers_with_shifts]
    
    # Find absent workers
    absent = [w for w in active_workers if w.id not in workers_with_shifts_ids]
    
    return {
        "date": today.isoformat(),
        "active_workers_total": len(active_workers),
        "worked_today": len(workers_with_shifts_ids),
        "absent_count": len(absent),
        "absent_workers": absent
    }

# ============================================================================
# SHIFT DURATION ANALYSIS
# ============================================================================

@router.get("/type/{shift_type}/analysis")
def analyze_shift_type(
    shift_type: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Analyze shifts of a specific type (morning, afternoon, night).
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    shifts = db.query(ShiftLog).filter(
        (ShiftLog.shift_type == shift_type) &
        (ShiftLog.date >= cutoff_date) &
        (ShiftLog.clock_out != None)
    ).all()
    
    if not shifts:
        return {
            "shift_type": shift_type,
            "period_days": days,
            "total_shifts": 0,
            "message": "No shifts found"
        }
    
    total_hours = 0
    for shift in shifts:
        if shift.clock_in and shift.clock_out:
            hours = (shift.clock_out - shift.clock_in).total_seconds() / 3600
            total_hours += hours
    
    return {
        "shift_type": shift_type,
        "period_days": days,
        "total_shifts": len(shifts),
        "total_hours": round(total_hours, 2),
        "average_shift_duration": round(total_hours / len(shifts), 2),
        "unique_workers": db.query(func.count(func.distinct(ShiftLog.worker_id))).filter(
            (ShiftLog.shift_type == shift_type) &
            (ShiftLog.date >= cutoff_date)
        ).scalar()
    }

# ============================================================================
# BULK CLOCK OUT
# ============================================================================

@router.post("/bulk/clock-out")
def bulk_clock_out(
    shift_ids: List[int],
    db: Session = Depends(get_db)
):
    """
    Clock out multiple workers at once (end of shift period).
    """
    shifts = db.query(ShiftLog).filter(ShiftLog.id.in_(shift_ids)).all()
    
    if not shifts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No shifts found"
        )
    
    clocked_out = 0
    for shift in shifts:
        if not shift.clock_out:
            shift.clock_out = datetime.utcnow()
            shift.status = "completed"
            clocked_out += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Clocked out {clocked_out} workers",
        "clocked_out_count": clocked_out
    }

# ============================================================================
# SYNC ENDPOINTS (OFFLINE SUPPORT)
# ============================================================================

@router.get("/sync/pending")
def get_unsynced_shifts(db: Session = Depends(get_db)):
    """Get all shifts that haven't been synced."""
    unsynced = db.query(ShiftLog).filter(ShiftLog.synced == False).all()
    
    return {
        "unsynced_count": len(unsynced),
        "shifts": unsynced
    }

@router.post("/sync/mark-synced")
def mark_shifts_synced(shift_ids: List[int], db: Session = Depends(get_db)):
    """Mark shifts as synced after cloud upload."""
    shifts = db.query(ShiftLog).filter(ShiftLog.id.in_(shift_ids)).all()
    
    if not shifts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No shifts found"
        )
    
    for shift in shifts:
        shift.synced = True
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Marked {len(shifts)} shifts as synced"
    }
