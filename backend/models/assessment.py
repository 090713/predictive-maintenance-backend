"""
Assessment model - represents a prediction assessment for a machine.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from bson import ObjectId

from backend.schemas import PredictionResponse


class AssessmentBase(BaseModel):
    """Base assessment model matching prediction response + metadata."""
    machine_id: str
    mission_id: str
    user_id: str
    inputs: Dict[str, Any] = Field(description="Raw sensor inputs")
    prediction: PredictionResponse
    source: Literal["fastapi", "gradio", "simulated"] = "fastapi"


class AssessmentCreate(AssessmentBase):
    """Model for creating a new assessment."""
    pass


class AssessmentInDB(AssessmentBase):
    """Assessment model as stored in database."""
    id: str = Field(alias="_id")
    ts: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class AssessmentResponse(BaseModel):
    """Assessment model for API responses."""
    id: str
    machine_id: str
    mission_id: str
    user_id: str
    ts: datetime
    source: str
    # Key metrics for list views
    failure_probability: float
    health_status: str
    risk_level: str
    predicted_class: str
    failure_mode: Optional[str]
    anomaly_percentile: float

    @classmethod
    def from_db(cls, assessment: AssessmentInDB) -> "AssessmentResponse":
        pred = assessment.prediction
        return cls(
            id=assessment.id,
            machine_id=assessment.machine_id,
            mission_id=assessment.mission_id,
            user_id=assessment.user_id,
            ts=assessment.ts,
            source=assessment.source,
            failure_probability=pred.failure_probability,
            health_status=pred.health_status,
            risk_level=pred.risk_level,
            predicted_class=pred.predicted_class,
            failure_mode=pred.failure_mode,
            anomaly_percentile=pred.anomaly_percentile,
        )


class AssessmentDetailResponse(AssessmentResponse):
    """Full assessment detail for single-item view."""
    inputs: Dict[str, Any]
    prediction: PredictionResponse


class AssessmentListQuery(BaseModel):
    """Query parameters for listing assessments."""
    mission_id: Optional[str] = None
    machine_id: Optional[str] = None
    user_id: Optional[str] = None
    health_status: Optional[str] = None
    risk_level: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AssessmentListResponse(BaseModel):
    """Paginated assessment list response."""
    items: List[AssessmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int