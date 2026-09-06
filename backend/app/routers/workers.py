"""
Worker Management API Routes
Handles HR, workforce, and employee data
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import Worker, ShiftLog
from app.schemas import WorkerCreate, WorkerUpdate, WorkerResponse

router = APIRouter()

# ============================================================================
# CREATE WORKER
# ============================================================================

@router.post("/", response_model=WorkerResponse, status_code=status.HTTP_201_CREATED)
def create_worker(worker: WorkerCreate, db: Session = Depends(get_db)):
    """
    Create a new worker/employee.
    
    - **employee_id**: Unique employee identifier (e.g., "EMP-001")
    - **first_name**: Worker's first name
    - **last_name**: Worker's last name
    - **email**: Email address (must be unique)
    - **phone**: Contact phone number
    - **role**: Job title (Driver, Operator, Supervisor, Manager, etc.)
    - **department**: Department (Fleet, Operations, HR, Maintenance, etc.)
    - **date_hired**: Hire date
    """
    # Check if employee already exists
    existing = db.query(Worker).filter(
        (Worker.employee_id == worker.employee_id) |
        (Worker.email == worker.email)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee with this ID or email already exists"
        )
    
    db_worker = Worker(**worker.dict())
    db.add(db_worker)
    db.commit()
    db.refresh(db_worker)
    
    return db_worker

# ============================================================================
# GET ALL WORKERS
# ============================================================================

@router.get("/", response_model=List[WorkerResponse])
def get_workers(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    role: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all workers with pagination and optional filtering.
    
    - **skip**: Number of records to skip
    - **limit**: Maximum records to return
    - **role**: Filter by job role
    - **department**: Filter by department
    - **status**: Filter by status (active, inactive, leave)
    """
    query = db.query(Worker)
    
    if role:
        query = query.filter(Worker.role == role)
    if department:
        query = query.filter(Worker.department == department)
    if status:
        query = query.filter(Worker.status == status)
    
    workers = query.offset(skip).limit(limit).all()
    return workers

# ============================================================================
# GET WORKER BY ID
# ============================================================================

@router.get("/{worker_id}", response_model=WorkerResponse)
def get_worker(worker_id: int, db: Session = Depends(get_db)):
    """
    Get a specific worker by ID.
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {worker_id} not found"
        )
    
    return worker

# ============================================================================
# GET WORKER BY EMPLOYEE_ID
# ============================================================================

@router.get("/search/{employee_id}")
def search_worker(employee_id: str, db: Session = Depends(get_db)):
    """
    Search for worker by employee_id.
    """
    worker = db.query(Worker).filter(Worker.employee_id == employee_id).first()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with employee ID '{employee_id}' not found"
        )
    
    return worker

# ============================================================================
# UPDATE WORKER
# ============================================================================

@router.put("/{worker_id}", response_model=WorkerResponse)
def update_worker(
    worker_id: int,
    worker_update: WorkerUpdate,
    db: Session = Depends(get_db)
):
    """
    Update worker information.
    Only provided fields will be updated.
    """
    db_worker = db.query(Worker).filter(Worker.id == worker_id).first()
    
    if not db_worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {worker_id} not found"
        )
    
    # Update only provided fields
    update_data = worker_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_worker, field, value)
    
    db.commit()
    db.refresh(db_worker)
    
    return db_worker

# ============================================================================
# UPDATE WORKER STATUS
# ============================================================================

@router.patch("/{worker_id}/status", response_model=WorkerResponse)
def update_worker_status(
    worker_id: int,
    new_status: str = Query(..., regex="^(active|inactive|leave)$"),
    db: Session = Depends(get_db)
):
    """
    Update worker status (active, inactive, leave).
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {worker_id} not found"
        )
    
    worker.status = new_status
    db.commit()
    db.refresh(worker)
    
    return worker

# ============================================================================
# DELETE WORKER
# ============================================================================

@router.delete("/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_worker(worker_id: int, db: Session = Depends(get_db)):
    """
    Delete a worker record.
    WARNING: This is a hard delete and cannot be undone.
    Consider marking as inactive instead.
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {worker_id} not found"
        )
    
    db.delete(worker)
    db.commit()

# ============================================================================
# WORKER STATISTICS
# ============================================================================

@router.get("/stats/summary")
def get_worker_stats(db: Session = Depends(get_db)):
    """
    Get summary statistics about workforce.
    """
    total_workers = db.query(Worker).count()
    active_workers = db.query(Worker).filter(Worker.status == "active").count()
    inactive_workers = db.query(Worker).filter(Worker.status == "inactive").count()
    on_leave = db.query(Worker).filter(Worker.status == "leave").count()
    
    # Get role distribution
    roles = {}
    for role_obj in db.query(Worker.role, func.count(Worker.id)).group_by(Worker.role).all():
        roles[role_obj[0]] = role_obj[1]
    
    # Get department distribution
    departments = {}
    for dept_obj in db.query(Worker.department, func.count(Worker.id)).group_by(Worker.department).all():
        departments[dept_obj[0]] = dept_obj[1]
    
    return {
        "total_workers": total_workers,
        "active": active_workers,
        "inactive": inactive_workers,
        "on_leave": on_leave,
        "by_role": roles,
        "by_department": departments,
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# GET WORKERS BY DEPARTMENT
# ============================================================================

@router.get("/department/{department}")
def get_workers_by_department(
    department: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all workers in a specific department.
    """
    workers = db.query(Worker).filter(
        Worker.department == department
    ).offset(skip).limit(limit).all()
    
    return workers

# ============================================================================
# GET WORKERS BY ROLE
# ============================================================================

@router.get("/role/{role}")
def get_workers_by_role(
    role: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all workers with a specific role/title.
    """
    workers = db.query(Worker).filter(
        Worker.role == role
    ).offset(skip).limit(limit).all()
    
    return workers

# ============================================================================
# GET ACTIVE WORKERS
# ============================================================================

@router.get("/active")
def get_active_workers(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all active workers (not on leave, not inactive).
    """
    workers = db.query(Worker).filter(
        Worker.status == "active"
    ).offset(skip).limit(limit).all()
    
    return workers

# ============================================================================
# WORKER PROFILE WITH SHIFT HISTORY
# ============================================================================

@router.get("/{worker_id}/profile")
def get_worker_profile(worker_id: int, db: Session = Depends(get_db)):
    """
    Get detailed worker profile including recent shift history.
    """
    from sqlalchemy import func
    
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with ID {worker_id} not found"
        )
    
    # Get recent shifts
    recent_shifts = db.query(ShiftLog).filter(
        ShiftLog.worker_id == worker_id
    ).order_by(desc(ShiftLog.date)).limit(10).all()
    
    # Calculate total hours worked
    total_hours = 0
    for shift in recent_shifts:
        if shift.clock_out:
            hours = (shift.clock_out - shift.clock_in).total_seconds() / 3600
            total_hours += hours
    
    return {
        "worker": worker,
        "recent_shifts": recent_shifts,
        "total_hours_recent": round(total_hours, 2),
        "days_since_hired": (datetime.utcnow() - worker.date_hired).days
    }

# ============================================================================
# BULK OPERATIONS
# ============================================================================

@router.post("/bulk/status-update")
def bulk_update_status(
    worker_ids: List[int],
    new_status: str = Query(..., regex="^(active|inactive|leave)$"),
    db: Session = Depends(get_db)
):
    """
    Update status for multiple workers at once.
    """
    workers = db.query(Worker).filter(Worker.id.in_(worker_ids)).all()
    
    if not workers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No workers found with provided IDs"
        )
    
    for worker in workers:
        worker.status = new_status
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Updated status for {len(workers)} workers",
        "updated_count": len(workers)
    }

# ============================================================================
# EXPORT WORKERS
# ============================================================================

@router.get("/export/all")
def export_workers(db: Session = Depends(get_db)):
    """
    Export all worker data in JSON format.
    Useful for reports and backups.
    """
    workers = db.query(Worker).all()
    
    return {
        "total_workers": len(workers),
        "export_date": datetime.utcnow().isoformat(),
        "workers": workers
    }

# ============================================================================
# NEW HIRES (Recently hired workers)
# ============================================================================

@router.get("/recent/new-hires")
def get_new_hires(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get workers hired in the last N days.
    """
    from datetime import timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    new_hires = db.query(Worker).filter(
        Worker.date_hired >= cutoff_date
    ).order_by(desc(Worker.date_hired)).all()
    
    return {
        "period_days": days,
        "new_hires_count": len(new_hires),
        "workers": new_hires
    }
