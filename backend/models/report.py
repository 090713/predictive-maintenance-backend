"""
Report model - represents a generated report for a time period.
"""
from datetime import datetime
from typing import List, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId


class ReportFormat(str, Enum):
    """Report output format."""
    CSV = "csv"
    XLSX = "xlsx"


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class ReportBase(BaseModel):
    """Base report model."""
    requested_by: str
    mission_ids: List[str] = Field(default_factory=list)
    machine_ids: List[str] = Field(default_factory=list)
    date_from: datetime
    date_to: datetime
    format: ReportFormat = ReportFormat.CSV
    include_derived: bool = True
    include_features: bool = True


class ReportCreate(ReportBase):
    """Model for creating a new report."""
    pass


class ReportInDB(ReportBase):
    """Report model as stored in database."""
    id: str = Field(alias="_id")
    status: ReportStatus = ReportStatus.PENDING
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    record_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class ReportResponse(ReportBase):
    """Report model for API responses."""
    id: str
    status: ReportStatus
    file_path: Optional[str]
    file_size: Optional[int]
    record_count: int
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    @classmethod
    def from_db(cls, report: "ReportInDB") -> "ReportResponse":
        return cls(
            id=report.id,
            requested_by=report.requested_by,
            mission_ids=report.mission_ids,
            machine_ids=report.machine_ids,
            date_from=report.date_from,
            date_to=report.date_to,
            format=report.format,
            include_derived=report.include_derived,
            include_features=report.include_features,
            status=report.status,
            file_path=report.file_path,
            file_size=report.file_size,
            record_count=report.record_count,
            error_message=report.error_message,
            created_at=report.created_at,
            updated_at=report.updated_at,
            completed_at=report.completed_at,
        )


class ReportListQuery(BaseModel):
    """Query parameters for listing reports."""
    status: Optional[ReportStatus] = None
    requested_by: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ReportListResponse(BaseModel):
    """Paginated report list response."""
    items: List[ReportResponse]
    total: int
    page: int
    page_size: int
    total_pages: int