"""
SQLAlchemy ORM Models for African Chrome Fields Management System
Defines database tables and relationships for mining operations
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

# ============================================================================
# ENUMS (Fixed value types for consistency)
# ============================================================================

class VehicleStatus(str, enum.Enum):
    """Status of mining vehicles"""
    OPERATIONAL = "operational"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"

class ShiftStatus(str, enum.Enum):
    """Status of work shifts"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class EquipmentStatus(str, enum.Enum):
    """Status of mining equipment"""
    WORKING = "working"
    IDLE = "idle"
    MAINTENANCE = "maintenance"
    BROKEN = "broken"

# ============================================================================
# FLEET & LOGISTICS MODELS
# ============================================================================

class Vehicle(Base):
    """Mining vehicles (trucks, excavators, loaders)"""
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(String(50), unique=True, index=True)  # E.g., "TRUCK-001"
    vehicle_type = Column(String(100))  # E.g., "Haulage Truck", "Excavator"
    make = Column(String(100))  # E.g., "Volvo", "Caterpillar"
    model = Column(String(100))
    year = Column(Integer)
    registration = Column(String(50), unique=True)  # License plate
    status = Column(String(50), default=VehicleStatus.OPERATIONAL)
    fuel_capacity = Column(Float)  # Liters
    current_fuel = Column(Float, default=0)  # Current fuel level
    last_maintenance = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    fuel_logs = relationship("FuelLog", back_populates="vehicle")
    loads = relationship("OreLoad", back_populates="vehicle")

class FuelLog(Base):
    """Daily fuel consumption tracking"""
    __tablename__ = "fuel_logs"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    fuel_amount = Column(Float)  # Liters added
    cost = Column(Float)  # Currency amount
    date = Column(DateTime, default=datetime.utcnow)
    odometer_reading = Column(Float)  # Kilometers
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    synced = Column(Boolean, default=False)  # For offline sync tracking

    # Relationships
    vehicle = relationship("Vehicle", back_populates="fuel_logs")

class OreLoad(Base):
    """Truck load of chrome ore"""
    __tablename__ = "ore_loads"

    id = Column(Integer, primary_key=True, index=True)
    load_number = Column(String(100), unique=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    weight_kg = Column(Float)  # Total weight in kilograms
    ore_grade = Column(String(50))  # E.g., "Premium", "Standard"
    origin_pit = Column(String(100))  # Which pit it came from
    destination = Column(String(100))  # Processing plant or storage
    loaded_at = Column(DateTime, default=datetime.utcnow)
    unloaded_at = Column(DateTime, nullable=True)
    driver_id = Column(Integer, ForeignKey("workers.id"))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    synced = Column(Boolean, default=False)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="loads")
    driver = relationship("Worker", back_populates="loads")
    weighbridge = relationship("WeighbridgeTicket", back_populates="load")

class WeighbridgeTicket(Base):
    """Weighbridge measurement data"""
    __tablename__ = "weighbridge_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(100), unique=True, index=True)
    load_id = Column(Integer, ForeignKey("ore_loads.id"))
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    gross_weight = Column(Float)  # kg - total with truck
    tare_weight = Column(Float)  # kg - truck empty weight
    net_weight = Column(Float)  # kg - ore only
    weighed_at = Column(DateTime, default=datetime.utcnow)
    operator_id = Column(Integer, ForeignKey("workers.id"))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    synced = Column(Boolean, default=False)

    # Relationships
    load = relationship("OreLoad", back_populates="weighbridge")
    vehicle = relationship("Vehicle")

# ============================================================================
# OPERATIONS & EQUIPMENT MODELS
# ============================================================================

class Equipment(Base):
    """Heavy machinery and equipment"""
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(String(50), unique=True, index=True)  # E.g., "EXC-001"
    equipment_type = Column(String(100))  # E.g., "Excavator", "Drill"
    make = Column(String(100))
    model = Column(String(100))
    status = Column(String(50), default=EquipmentStatus.WORKING)
    hours_operated = Column(Float, default=0)  # Total operating hours
    last_maintenance = Column(DateTime)
    next_maintenance = Column(DateTime)
    location = Column(String(200))  # Current pit/site
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    inspections = relationship("EquipmentInspection", back_populates="equipment")
    maintenance = relationship("MaintenanceLog", back_populates="equipment")

class EquipmentInspection(Base):
    """Daily equipment safety/status checks"""
    __tablename__ = "equipment_inspections"

    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"))
    inspector_id = Column(Integer, ForeignKey("workers.id"))
    status = Column(String(50))  # "OK", "Issue", "Critical"
    observations = Column(Text)
    checked_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    synced = Column(Boolean, default=False)

    # Relationships
    equipment = relationship("Equipment", back_populates="inspections")
    inspector = relationship("Worker")

class MaintenanceLog(Base):
    """Equipment maintenance history"""
    __tablename__ = "maintenance_logs"

    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"))
    maintenance_type = Column(String(100))  # "Service", "Repair", "Oil Change"
    description = Column(Text)
    cost = Column(Float)
    maintenance_date = Column(DateTime, default=datetime.utcnow)
    technician = Column(String(100))
    parts_replaced = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    equipment = relationship("Equipment", back_populates="maintenance")

# ============================================================================
# HR & WORKFORCE MODELS
# ============================================================================

class Worker(Base):
    """Employees and contractors"""
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20))
    role = Column(String(100))  # "Driver", "Operator", "Supervisor", "Manager"
    department = Column(String(100))  # "Fleet", "Operations", "HR"
    date_hired = Column(DateTime)
    status = Column(String(50), default="active")  # "active", "inactive", "leave"
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    shifts = relationship("ShiftLog", back_populates="worker")
    loads = relationship("OreLoad", back_populates="driver")
    incidents = relationship("Incident", back_populates="reported_by")

class ShiftLog(Base):
    """Worker shift tracking (clock in/out)"""
    __tablename__ = "shift_logs"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    date = Column(DateTime, default=datetime.utcnow)
    clock_in = Column(DateTime)
    clock_out = Column(DateTime, nullable=True)
    status = Column(String(50), default=ShiftStatus.ACTIVE)  # "active", "completed"
    location = Column(String(200))  # GPS/Site location
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    synced = Column(Boolean, default=False)

    # Relationships
    worker = relationship("Worker", back_populates="shifts")

class Incident(Base):
    """Safety incidents and near-misses"""
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_type = Column(String(100))  # "Accident", "Near-miss", "Injury"
    reported_by_id = Column(Integer, ForeignKey("workers.id"))
    description = Column(Text)
    severity = Column(String(50))  # "Low", "Medium", "High", "Critical"
    location = Column(String(200))
    date = Column(DateTime, default=datetime.utcnow)
    action_taken = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    synced = Column(Boolean, default=False)

    # Relationships
    reported_by = relationship("Worker", back_populates="incidents")

# ============================================================================
# INVENTORY MODELS
# ============================================================================

class Spare(Base):
    """Spare parts inventory"""
    __tablename__ = "spares"

    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String(100), unique=True, index=True)
    part_name = Column(String(200))
    category = Column(String(100))  # "Engine", "Hydraulic", "Electrical"
    quantity = Column(Integer, default=0)
    unit_cost = Column(Float)
    supplier = Column(String(200))
    location = Column(String(200))  # Storage location
    reorder_level = Column(Integer)  # Alert when below this
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    usage_logs = relationship("SpareUsage", back_populates="spare")

class SpareUsage(Base):
    """Track when spares are used"""
    __tablename__ = "spare_usage"

    id = Column(Integer, primary_key=True, index=True)
    spare_id = Column(Integer, ForeignKey("spares.id"))
    equipment_id = Column(Integer, ForeignKey("equipment.id"))
    quantity_used = Column(Integer)
    used_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    synced = Column(Boolean, default=False)

    # Relationships
    spare = relationship("Spare", back_populates="usage_logs")
