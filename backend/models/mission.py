"""
Mission model - represents a maintenance mission/project.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class MissionBase(BaseModel):
    """Base mission model."""
    mission_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=128)
    type: str = Field(min_length=1, max_length=64, description="Free-text mission type/category")
    description: Optional[str] = Field(default=None, max_length=500)


class MissionCreate(MissionBase):
    """Model for creating a new mission."""
    pass


class MissionUpdate(BaseModel):
    """Model for updating a mission."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    type: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=500)


class MissionInDB(MissionBase):
    """Mission model as stored in database."""
    id: str = Field(alias="_id")
    assigned_worker_ids: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class MissionResponse(MissionBase):
    """Mission model for API responses."""
    id: str
    assigned_worker_ids: List[str]
    machine_count: int = 0
    worker_count: int = 0
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, mission: MissionInDB, machine_count: int = 0) -> "MissionResponse":
        return cls(
            id=mission.id,
            mission_id=mission.mission_id,
            name=mission.name,
            type=mission.type,
            description=mission.description,
            assigned_worker_ids=mission.assigned_worker_ids,
            machine_count=machine_count,
            worker_count=len(mission.assigned_worker_ids),
            created_at=mission.created_at,
            updated_at=mission.updated_at,
        )


class MissionListResponse(BaseModel):
    """Paginated mission list response."""
    items: List[MissionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int