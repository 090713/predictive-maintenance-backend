"""
Machine model - simplified for predictive maintenance agent.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from bson import ObjectId


class MachineCreate(BaseModel):
    """Model for creating a new machine."""
    machine_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=128)
    type: Optional[str] = Field(default=None, max_length=64, description="Machine type (e.g., Lathe, CNC, Motor)")
    location: Optional[str] = Field(default=None, max_length=128)
    sensor_values: Optional[Dict[str, Any]] = Field(default=None, description="Current sensor readings")


class MachineUpdate(BaseModel):
    """Model for updating a machine's sensor values."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    type: Optional[str] = Field(default=None, max_length=64)
    location: Optional[str] = Field(default=None, max_length=128)
    sensor_values: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class MachineInDB(BaseModel):
    """Machine model as stored in database."""
    id: str = Field(alias="_id")
    machine_id: str
    name: str
    type: Optional[str] = None
    location: Optional[str] = None
    sensor_values: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class MachineResponse(BaseModel):
    """Machine model for API responses."""
    id: str
    machine_id: str
    name: str
    type: Optional[str] = None
    location: Optional[str] = None
    sensor_values: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    assessment_count: int = 0
    latest_health_status: Optional[str] = None
    latest_risk_level: Optional[str] = None
    latest_assessment_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, machine: MachineInDB, assessment_count: int = 0) -> "MachineResponse":
        return cls(
            id=machine.id,
            machine_id=machine.machine_id,
            name=machine.name,
            type=machine.type,
            location=machine.location,
            sensor_values=machine.sensor_values,
            is_active=machine.is_active,
            assessment_count=assessment_count,
            created_at=machine.created_at,
            updated_at=machine.updated_at,
        )


class MachineListResponse(BaseModel):
    """Paginated machine list response."""
    items: List[MachineResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
