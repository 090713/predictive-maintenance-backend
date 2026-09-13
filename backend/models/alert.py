"""
Alert model - represents an alert generated from assessments.
"""
from datetime import datetime
from typing import List, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId


class AlertStatus(str, Enum):
    """Alert status states."""
    OPEN = "Open"
    ACKNOWLEDGED = "Acknowledged"
    RESOLVED = "Resolved"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    WARNING = "Warning"
    HIGH = "High"
    CRITICAL = "Critical"


class AlertBase(BaseModel):
    """Base alert model."""
    assessment_id: str
    machine_id: str
    mission_id: str
    severity: AlertSeverity
    failure_probability: float
    risk_level: str
    mode_code: str
    mode_name: str
    evidence: List[str] = Field(default_factory=list)
    recommendation: str


class AlertCreate(AlertBase):
    """Model for creating a new alert."""
    pass


class AlertInDB(AlertBase):
    """Alert model as stored in database."""
    id: str = Field(alias="_id")
    status: AlertStatus = AlertStatus.OPEN
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    ts: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class AlertResponse(AlertBase):
    """Alert model for API responses."""
    id: str
    status: AlertStatus
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    ts: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, alert: AlertInDB) -> "AlertResponse":
        return cls(
            id=alert.id,
            assessment_id=alert.assessment_id,
            machine_id=alert.machine_id,
            mission_id=alert.mission_id,
            severity=alert.severity,
            failure_probability=alert.failure_probability,
            risk_level=alert.risk_level,
            mode_code=alert.mode_code,
            mode_name=alert.mode_name,
            evidence=alert.evidence,
            recommendation=alert.recommendation,
            status=alert.status,
            acknowledged_by=alert.acknowledged_by,
            acknowledged_at=alert.acknowledged_at,
            resolved_by=alert.resolved_by,
            resolved_at=alert.resolved_at,
            ts=alert.ts,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
        )


class AlertListQuery(BaseModel):
    """Query parameters for listing alerts."""
    mission_id: Optional[str] = None
    machine_id: Optional[str] = None
    status: Optional[AlertStatus] = None
    severity: Optional[AlertSeverity] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AlertListResponse(BaseModel):
    """Paginated alert list response."""
    items: List[AlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AlertActionRequest(BaseModel):
    """Request for alert actions (acknowledge/resolve)."""
    pass