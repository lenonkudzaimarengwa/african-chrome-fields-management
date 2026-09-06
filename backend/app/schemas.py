"""
Pydantic Schemas for API Request/Response Validation
African Chrome Fields Management System
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ============================================================================
# ENUMS (matching database enums)
# ============================================================================

class VehicleStatusSchema(str, Enum):
    OPERATIONAL = "operational"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"

class ShiftStatusSchema(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class EquipmentStatusSchema(str, Enum):
    WORKING = "working"
    IDLE = "idle"
    MAINTENANCE = "maintenance"
    BROKEN = "broken"

# ============================================================================
# VEHICLE SCHEMAS
# ============================================================================

class VehicleBase(BaseModel):
    """Base vehicle data"""
    vehicle_id: str = Field(..., min_length=1, max_length=50)
    vehicle_type: str
    make: str
    model: str
    year: int = Field(..., ge=1900, le=2100)
    registration: str = Field(..., min_length=1, max_length=50)
    fuel_capacity: float = Field(..., gt=0)
    notes: Optional[str] = None

class VehicleCreate(VehicleBase):
    """Schema for creating a vehicle"""
    pass

class VehicleUpdate(BaseModel):
    """Schema for updating a vehicle"""
    vehicle_type: Optional[str] = None
    status: Optional[VehicleStatusSchema] = None
    current_fuel: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None

class VehicleResponse(VehicleBase):
    """Schema for vehicle response"""
    id: int
    status: VehicleStatusSchema
    current_fuel: float
    last_maintenance: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# FUEL LOG SCHEMAS
# ============================================================================

class FuelLogBase(BaseModel):
    """Base fuel log data"""
    vehicle_id: int
    fuel_amount: float = Field(..., gt=0)
    cost: float = Field(..., ge=0)
    odometer_reading: float = Field(..., ge=0)
    notes: Optional[str] = None

class FuelLogCreate(FuelLogBase):
    """Schema for creating fuel log"""
    pass

class FuelLogResponse(FuelLogBase):
    """Schema for fuel log response"""
    id: int
    date: datetime
    synced: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# ORE LOAD SCHEMAS
# ============================================================================

class OreLoadBase(BaseModel):
    """Base ore load data"""
    load_number: str = Field(..., min_length=1, max_length=100)
    vehicle_id: int
    weight_kg: float = Field(..., gt=0)
    ore_grade: str
    origin_pit: str
    destination: str
    driver_id: int
    notes: Optional[str] = None

class OreLoadCreate(OreLoadBase):
    """Schema for creating ore load"""
    pass

class OreLoadUpdate(BaseModel):
    """Schema for updating ore load"""
    unloaded_at: Optional[datetime] = None
    notes: Optional[str] = None

class OreLoadResponse(OreLoadBase):
    """Schema for ore load response"""
    id: int
    loaded_at: datetime
    unloaded_at: Optional[datetime]
    created_at: datetime
    synced: bool

    class Config:
        from_attributes = True

# ============================================================================
# WEIGHBRIDGE TICKET SCHEMAS
# ============================================================================

class WeighbridgeTicketBase(BaseModel):
    """Base weighbridge ticket data"""
    ticket_number: str = Field(..., min_length=1, max_length=100)
    load_id: int
    vehicle_id: int
    gross_weight: float = Field(..., gt=0)
    tare_weight: float = Field(..., ge=0)
    net_weight: float = Field(..., gt=0)
    operator_id: int
    notes: Optional[str] = None

    @validator('net_weight')
    def validate_net_weight(cls, v, values):
        """Ensure net_weight = gross_weight - tare_weight (within tolerance)"""
        if 'gross_weight' in values and 'tare_weight' in values:
            expected = values['gross_weight'] - values['tare_weight']
            # Allow 1% tolerance
            tolerance = expected * 0.01
            if abs(v - expected) > tolerance:
                raise ValueError('net_weight must equal gross_weight - tare_weight')
        return v

class WeighbridgeTicketCreate(WeighbridgeTicketBase):
    """Schema for creating weighbridge ticket"""
    pass

class WeighbridgeTicketResponse(WeighbridgeTicketBase):
    """Schema for weighbridge ticket response"""
    id: int
    weighed_at: datetime
    synced: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# EQUIPMENT SCHEMAS
# ============================================================================

class EquipmentBase(BaseModel):
    """Base equipment data"""
    equipment_id: str = Field(..., min_length=1, max_length=50)
    equipment_type: str
    make: str
    model: str
    location: str
    notes: Optional[str] = None

class EquipmentCreate(EquipmentBase):
    """Schema for creating equipment"""
    pass

class EquipmentUpdate(BaseModel):
    """Schema for updating equipment"""
    status: Optional[EquipmentStatusSchema] = None
    hours_operated: Optional[float] = Field(None, ge=0)
    location: Optional[str] = None
    next_maintenance: Optional[datetime] = None
    notes: Optional[str] = None

class EquipmentResponse(EquipmentBase):
    """Schema for equipment response"""
    id: int
    status: EquipmentStatusSchema
    hours_operated: float
    last_maintenance: Optional[datetime]
    next_maintenance: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# EQUIPMENT INSPECTION SCHEMAS
# ============================================================================

class EquipmentInspectionBase(BaseModel):
    """Base equipment inspection data"""
    equipment_id: int
    inspector_id: int
    status: str = Field(..., regex="^(OK|Issue|Critical)$")
    observations: str

class EquipmentInspectionCreate(EquipmentInspectionBase):
    """Schema for creating equipment inspection"""
    pass

class EquipmentInspectionResponse(EquipmentInspectionBase):
    """Schema for equipment inspection response"""
    id: int
    checked_at: datetime
    synced: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# MAINTENANCE LOG SCHEMAS
# ============================================================================

class MaintenanceLogBase(BaseModel):
    """Base maintenance log data"""
    equipment_id: int
    maintenance_type: str
    description: str
    cost: float = Field(..., ge=0)
    technician: str
    parts_replaced: Optional[str] = None

class MaintenanceLogCreate(MaintenanceLogBase):
    """Schema for creating maintenance log"""
    pass

class MaintenanceLogResponse(MaintenanceLogBase):
    """Schema for maintenance log response"""
    id: int
    maintenance_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# WORKER SCHEMAS
# ============================================================================

class WorkerBase(BaseModel):
    """Base worker data"""
    employee_id: str = Field(..., min_length=1, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=7, max_length=20)
    role: str
    department: str
    notes: Optional[str] = None

class WorkerCreate(WorkerBase):
    """Schema for creating worker"""
    date_hired: datetime

class WorkerUpdate(BaseModel):
    """Schema for updating worker"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class WorkerResponse(WorkerBase):
    """Schema for worker response"""
    id: int
    date_hired: datetime
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# SHIFT LOG SCHEMAS
# ============================================================================

class ShiftLogBase(BaseModel):
    """Base shift log data"""
    worker_id: int
    clock_in: datetime
    location: str

class ShiftLogCreate(ShiftLogBase):
    """Schema for creating shift log"""
    pass

class ShiftLogUpdate(BaseModel):
    """Schema for updating shift log (clock out)"""
    clock_out: datetime
    notes: Optional[str] = None

class ShiftLogResponse(ShiftLogBase):
    """Schema for shift log response"""
    id: int
    date: datetime
    clock_out: Optional[datetime]
    status: ShiftStatusSchema
    notes: Optional[str]
    synced: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# INCIDENT SCHEMAS
# ============================================================================

class IncidentBase(BaseModel):
    """Base incident data"""
    incident_type: str = Field(..., regex="^(Accident|Near-miss|Injury)$")
    reported_by_id: int
    description: str
    severity: str = Field(..., regex="^(Low|Medium|High|Critical)$")
    location: str
    action_taken: Optional[str] = None

class IncidentCreate(IncidentBase):
    """Schema for creating incident"""
    pass

class IncidentResponse(IncidentBase):
    """Schema for incident response"""
    id: int
    date: datetime
    synced: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# SPARE PART SCHEMAS
# ============================================================================

class SpareBase(BaseModel):
    """Base spare part data"""
    part_number: str = Field(..., min_length=1, max_length=100)
    part_name: str = Field(..., min_length=1, max_length=200)
    category: str
    quantity: int = Field(..., ge=0)
    unit_cost: float = Field(..., gt=0)
    supplier: str
    location: str
    reorder_level: int = Field(..., ge=0)
    notes: Optional[str] = None

class SpareCreate(SpareBase):
    """Schema for creating spare part"""
    pass

class SpareUpdate(BaseModel):
    """Schema for updating spare part"""
    quantity: Optional[int] = Field(None, ge=0)
    location: Optional[str] = None
    reorder_level: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None

class SpareResponse(SpareBase):
    """Schema for spare part response"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# SPARE USAGE SCHEMAS
# ============================================================================

class SpareUsageBase(BaseModel):
    """Base spare usage data"""
    spare_id: int
    equipment_id: int
    quantity_used: int = Field(..., gt=0)
    notes: Optional[str] = None

class SpareUsageCreate(SpareUsageBase):
    """Schema for creating spare usage"""
    pass

class SpareUsageResponse(SpareUsageBase):
    """Schema for spare usage response"""
    id: int
    used_date: datetime
    synced: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# GENERIC RESPONSE SCHEMAS
# ============================================================================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[dict] = None

class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict] = None

class PaginatedResponse(BaseModel):
    """Generic paginated response"""
    total: int
    page: int
    page_size: int
    pages: int
    data: List[dict]

# ============================================================================
# STATISTICS SCHEMAS
# ============================================================================

class VehicleStatsResponse(BaseModel):
    """Vehicle fleet statistics"""
    total_vehicles: int
    operational_vehicles: int
    maintenance_vehicles: int
    total_fuel_consumed: float
    avg_fuel_per_vehicle: float
    last_updated: datetime

class OperationStatsResponse(BaseModel):
    """Mining operation statistics"""
    total_ore_loaded_kg: float
    total_ore_unloaded_kg: float
    avg_load_weight: float
    total_loads: int
    active_shifts: int
    completed_shifts: int
    incidents_today: int
    last_updated: datetime
