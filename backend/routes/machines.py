"""
Machine routes - simplified CRUD for predictive maintenance agent.
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query
from pymongo import DESCENDING
from bson import ObjectId

from backend.models.machine import MachineCreate, MachineUpdate, MachineResponse, MachineListResponse
from backend.models.assessment import AssessmentResponse
from backend.db.mongodb import get_collection


router = APIRouter(prefix="/api/v1/machines", tags=["Machines"])


async def get_machine_by_id(machine_id: str) -> Optional[dict]:
    """Get machine by machine_id string."""
    return await get_collection("machines").find_one({"machine_id": machine_id})


@router.post("", response_model=MachineResponse, status_code=status.HTTP_201_CREATED)
async def create_machine(machine_data: MachineCreate):
    """Register a new machine."""
    machines_collection = get_collection("machines")

    existing = await machines_collection.find_one({"machine_id": machine_data.machine_id})
    if existing:
        raise HTTPException(status_code=400, detail="Machine ID already exists")

    machine_doc = machine_data.model_dump(exclude_none=True)
    machine_doc["is_active"] = True
    machine_doc["created_at"] = datetime.now(timezone.utc)
    machine_doc["updated_at"] = datetime.now(timezone.utc)

    result = await machines_collection.insert_one(machine_doc)
    machine_doc["_id"] = str(result.inserted_id)

    return MachineResponse(**machine_doc)


@router.get("", response_model=MachineListResponse)
async def list_machines(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    machine_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """List all machines with pagination and search."""
    machines_collection = get_collection("machines")
    assessments_collection = get_collection("assessments")

    query = {}
    if machine_type:
        query["type"] = machine_type
    if search:
        query["$or"] = [
            {"machine_id": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}},
            {"type": {"$regex": search, "$options": "i"}},
            {"location": {"$regex": search, "$options": "i"}},
        ]

    total = await machines_collection.count_documents(query)
    total_pages = (total + page_size - 1) // page_size

    cursor = machines_collection.find(query).sort("created_at", DESCENDING).skip((page - 1) * page_size).limit(page_size)

    items = []
    async for machine_doc in cursor:
        machine_doc["_id"] = str(machine_doc["_id"])
        assessment_count = await assessments_collection.count_documents({"machine_id": machine_doc["machine_id"]})
        latest_assessment = await assessments_collection.find_one(
            {"machine_id": machine_doc["machine_id"]},
            sort=[("ts", -1)]
        )

        machine = MachineResponse.from_db(MachineResponse(**machine_doc), assessment_count=assessment_count)
        if latest_assessment:
            pred = latest_assessment.get("prediction", {})
            machine.latest_health_status = pred.get("health_status")
            machine.latest_risk_level = pred.get("risk_level")
            machine.latest_assessment_id = latest_assessment.get("_id")
        items.append(machine)

    return MachineListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{machine_id}", response_model=MachineResponse)
async def get_machine(machine_id: str):
    """Get a machine by ID."""
    machine_doc = await get_machine_by_id(machine_id)
    if not machine_doc:
        raise HTTPException(status_code=404, detail="Machine not found")

    assessments_collection = get_collection("assessments")
    assessment_count = await assessments_collection.count_documents({"machine_id": machine_id})
    latest_assessment = await assessments_collection.find_one(
        {"machine_id": machine_id},
        sort=[("ts", -1)]
    )

    machine_doc["_id"] = str(machine_doc["_id"])
    machine = MachineResponse.from_db(MachineResponse(**machine_doc), assessment_count=assessment_count)
    if latest_assessment:
        pred = latest_assessment.get("prediction", {})
        machine.latest_health_status = pred.get("health_status")
        machine.latest_risk_level = pred.get("risk_level")
        machine.latest_assessment_id = str(latest_assessment.get("_id"))

    return machine


@router.patch("/{machine_id}")
async def update_machine_sensor_values(
    machine_id: str,
    update_data: MachineUpdate,
):
    """
    Update machine sensor values and automatically run prediction.
    Returns both the updated machine and the new assessment.
    """
    from backend.model_service import predict_machine
    from backend.services.assessment import create_assessment
    from backend.services.alert import create_alert_from_assessment
    from backend.models.assessment import AssessmentCreate
    from backend.schemas import PredictionResponse

    machines_collection = get_collection("machines")

    machine_doc = await get_machine_by_id(machine_id)
    if not machine_doc:
        raise HTTPException(status_code=404, detail="Machine not found")

    # Build update document
    update_doc = update_data.model_dump(exclude_unset=True)
    update_doc["updated_at"] = datetime.now(timezone.utc)

    # Update sensor values if provided
    if update_data.sensor_values:
        machine_doc["sensor_values"] = update_data.sensor_values

    result = await machines_collection.find_one_and_update(
        {"machine_id": machine_id},
        {"$set": update_doc},
        return_document=True
    )

    # Auto-run prediction if sensor_values were provided
    assessment_doc = None
    if update_data.sensor_values:
        sv = update_data.sensor_values
        try:
            pred_result = predict_machine(
                product_type=machine_doc.get("type", "UNKNOWN"),
                air_temperature=sv.get("air_temperature", 298.1),
                process_temperature=sv.get("process_temperature", 308.6),
                rotational_speed=sv.get("rotational_speed", 1450),
                torque=sv.get("torque", 45),
                tool_wear=sv.get("tool_wear", 120),
            )
            pred_result["source"] = "fastapi"
        except Exception:
            pred_result = {
                "failure_probability": 0,
                "predicted_failure": False,
                "anomaly_score": 0,
                "anomaly_percentile": 0,
                "is_anomaly": False,
                "failure_modes": {},
                "health_status": "Normal",
                "failure_mode": None,
                "failure_mode_name": None,
                "explanation": "Prediction service unavailable",
                "maintenance_recommendation": "Check model service",
                "predicted_class": "UNKNOWN",
                "recommended_maintenance_action": "Check model service",
                "decision_threshold": 0.5,
                "risk_level": "Low",
                "urgency": "Routine",
                "likely_failure_modes": [],
                "contributing_features": [],
                "condition_evidence": [],
                "model_version": "unavailable",
                "prediction_id": "",
                "prediction_timestamp": datetime.now(timezone.utc).isoformat(),
                "latency_ms": 0,
                "source": "simulated",
            }

        assessment = AssessmentCreate(
            machine_id=machine_id,
            inputs=sv,
            prediction=PredictionResponse(**pred_result),
            source=pred_result.get("source", "fastapi"),
        )
        assessment_doc = await create_assessment(assessment)

        # Auto-create alert if high risk
        health_status = pred_result.get("health_status", "")
        if health_status in ("High Risk", "Critical"):
            await create_alert_from_assessment(assessment_doc)

    result["_id"] = str(result["_id"])
    machine = MachineResponse(**result)

    return {
        "machine": machine,
        "assessment": AssessmentResponse.from_db(assessment_doc) if assessment_doc else None,
    }


@router.delete("/{machine_id}")
async def delete_machine(machine_id: str):
    """Delete a machine."""
    machines_collection = get_collection("machines")
    result = await machines_collection.delete_one({"machine_id": machine_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Machine not found")
    return {"message": "Machine deleted successfully"}
