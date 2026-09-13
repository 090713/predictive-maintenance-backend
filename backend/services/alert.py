"""
Alert service - auto-creation from assessments.
"""

from datetime import datetime, timezone
from typing import Optional

from backend.models.alert import (
    AlertCreate,
    AlertInDB,
    AlertStatus,
    AlertSeverity,
)
from backend.models.assessment import AssessmentInDB
from backend.db.mongodb import get_collection


def map_severity(health_status: str, risk_level: str) -> AlertSeverity:
    """Map health status and risk level to alert severity."""

    if health_status == "Critical" or risk_level == "Critical":
        return AlertSeverity.CRITICAL

    if health_status == "High Risk" or risk_level == "High":
        return AlertSeverity.HIGH

    return AlertSeverity.WARNING


async def create_alert_from_assessment(
    assessment: AssessmentInDB,
) -> Optional[AlertInDB]:
    """
    Create an alert from an assessment if it is High Risk or Critical.

    The prediction is a Pydantic PredictionResponse model, so its
    values are accessed using attributes rather than dictionary .get().
    """

    pred = assessment.prediction

    health_status = pred.health_status
    risk_level = pred.risk_level

    # Only High Risk and Critical predictions create alerts.
    if health_status not in ("High Risk", "Critical"):
        return None

    severity = map_severity(health_status, risk_level)

    # Avoid creating duplicate alerts for the same assessment.
    existing = await get_collection("alerts").find_one(
        {"assessment_id": assessment.id}
    )

    if existing:
        return None

    alert = AlertCreate(
        assessment_id=assessment.id,
        machine_id=assessment.machine_id,
        severity=severity,
        failure_probability=pred.failure_probability,
        risk_level=risk_level,
        mode_code=pred.failure_mode or "UNKNOWN",
        mode_name=pred.failure_mode_name or "Unknown Failure",
        evidence=pred.condition_evidence,
        recommendation=pred.recommended_maintenance_action,
    )

    alerts_collection = get_collection("alerts")

    alert_doc = alert.model_dump()
    alert_doc["ts"] = datetime.now(timezone.utc)
    alert_doc["status"] = AlertStatus.OPEN

    result = await alerts_collection.insert_one(alert_doc)

    # Convert MongoDB ObjectId to the string expected by AlertInDB.
    alert_doc["_id"] = str(result.inserted_id)

    return AlertInDB(**alert_doc)