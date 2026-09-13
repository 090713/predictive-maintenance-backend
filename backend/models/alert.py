"""
Alert model - simplified for predictive maintenance agent.
"""
from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId


class AlertStatus(str, Enum):
    """Alert status states."""
    OPEN = "Open"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    WARNING = "Warning"
    HIGH = "High"
    CRITICAL = "Critical"


class AlertCreate(BaseModel):
    """Model for creating a new alert."""
    assessment_id: str
    machine_id: str
    severity: AlertSeverity
    failure_probability: float
    risk_level: str
    mode_code: str
    mode_name: str
    evidence: List[str] = Field(default_factory=list)
    recommendation: str


class AlertInDB(BaseModel):
    """Alert model as stored in database."""
    id: str = Field(alias="_id")
    assessment_id: str
    machine_id: str
    severity: AlertSeverity
    failure_probability: float
    risk_level: str
    mode_code: str
    mode_name: str
    evidence: List[str] = Field(default_factory=list)
    recommendation: str
    status: AlertStatus = AlertStatus.OPEN
    ts: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class AlertResponse(BaseModel):
    """Alert model for API responses."""
    id: str
    assessment_id: str
    machine_id: str
    severity: AlertSeverity
    failure_probability: float
    risk_level: str
    mode_code: str
    mode_name: str
    evidence: List[str]
    recommendation: str
    status: AlertStatus
    ts: datetime

    @classmethod
    def from_db(cls, alert: AlertInDB) -> "AlertResponse":
        return cls(
            id=alert.id,
            assessment_id=alert.assessment_id,
            machine_id=alert.machine_id,
            severity=alert.severity,
            failure_probability=alert.failure_probability,
            risk_level=alert.risk_level,
            mode_code=alert.mode_code,
            mode_name=alert.mode_name,
            evidence=alert.evidence,
            recommendation=alert.recommendation,
            status=alert.status,
            ts=alert.ts,
        )


class AlertListQuery(BaseModel):
    """Query parameters for listing alerts."""
    machine_id: Optional[str] = None
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
