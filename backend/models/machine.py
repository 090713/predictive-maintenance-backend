"""
Machine model - represents a physical machine under monitoring.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from bson import ObjectId


class MachineBase(BaseModel):
    """Base machine model."""
    machine_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9_-]+$")
    mission_id: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1, max_length=64, description="Machine type (e.g., pump, compressor, motor)")
    location: Optional[str] = Field(default=None, max_length=128)
    specs: Dict[str, Any] = Field(default_factory=dict, description="Machine specifications as JSON")


class MachineCreate(MachineBase):
    """Model for creating a new machine."""
    pass


class MachineUpdate(BaseModel):
    """Model for updating a machine."""
    type: Optional[str] = Field(default=None, min_length=1, max_length=64)
    location: Optional[str] = Field(default=None, max_length=128)
    specs: Optional[Dict[str, Any]] = None
    assigned_worker_ids: Optional[List[str]] = None


class MachineInDB(MachineBase):
    """Machine model as stored in database."""
    id: str = Field(alias="_id")
    assigned_worker_ids: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class MachineResponse(MachineBase):
    """Machine model for API responses."""
    id: str
    assigned_worker_ids: List[str]
    assessment_count: int = 0
    latest_health_status: Optional[str] = None
    latest_risk_level: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, machine: MachineInDB, assessment_count: int = 0) -> "MachineResponse":
        return cls(
            id=machine.id,
            machine_id=machine.machine_id,
            mission_id=machine.mission_id,
            type=machine.type,
            location=machine.location,
            specs=machine.specs,
            assigned_worker_ids=machine.assigned_worker_ids,
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


class MachineAssignWorkersRequest(BaseModel):
    """Request to assign workers to a machine."""
    worker_ids: List[str] = Field(min_length=1)