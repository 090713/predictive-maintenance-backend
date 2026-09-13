"""
Alert service - auto-creation from assessments.
"""
from datetime import datetime, timezone
from typing import Optional

from backend.models.alert import AlertCreate, AlertInDB, AlertStatus, AlertSeverity
from backend.models.assessment import AssessmentInDB
from backend.db.mongodb import get_collection


def map_severity(health_status: str, risk_level: str) -> AlertSeverity:
    """Map health status to alert severity."""
    if health_status == "Critical" or risk_level == "Critical":
        return AlertSeverity.CRITICAL
    if health_status == "High Risk" or risk_level == "High":
        return AlertSeverity.HIGH
    return AlertSeverity.WARNING


async def create_alert_from_assessment(assessment: AssessmentInDB) -> Optional[AlertInDB]:
    """Create an alert from an assessment if it meets severity criteria."""
    pred = assessment.prediction
    health_status = pred.get("health_status", "")
    risk_level = pred.get("risk_level", "")

    # Only create alerts for High Risk and Critical
    if health_status not in ("High Risk", "Critical"):
        return None

    severity = map_severity(health_status, risk_level)

    # Check if alert already exists for this assessment
    existing = await get_collection("alerts").find_one({"assessment_id": assessment.id})
    if existing:
        return None

    alert = AlertCreate(
        assessment_id=assessment.id,
        machine_id=assessment.machine_id,
        severity=severity,
        failure_probability=pred.get("failure_probability", 0),
        risk_level=risk_level,
        mode_code=pred.get("failure_mode") or "UNKNOWN",
        mode_name=pred.get("failure_mode_name") or "Unknown Failure",
        evidence=pred.get("condition_evidence", []),
        recommendation=pred.get("recommended_maintenance_action", ""),
    )

    alerts_collection = get_collection("alerts")

    alert_doc = alert.model_dump()
    alert_doc["ts"] = datetime.now(timezone.utc)
    alert_doc["status"] = AlertStatus.OPEN

    result = await alerts_collection.insert_one(alert_doc)
    alert_doc["_id"] = str(result.inserted_id)

    return AlertInDB(**alert_doc)
