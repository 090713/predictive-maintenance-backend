"""
Machine routes - CRUD and automatic predictive maintenance assessment.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query
from pymongo import DESCENDING
from starlette.concurrency import run_in_threadpool

from backend.models.machine import (
    MachineCreate,
    MachineUpdate,
    MachineResponse,
    MachineListResponse,
)
from backend.models.assessment import (
    AssessmentCreate,
    AssessmentInDB,
    AssessmentResponse,
)
from backend.db.mongodb import get_collection


router = APIRouter(
    prefix="/api/v1/machines",
    tags=["Machines"],
)


async def get_machine_by_id(machine_id: str) -> Optional[dict]:
    """Get a machine by its application-level machine_id."""
    return await get_collection("machines").find_one(
        {"machine_id": machine_id}
    )


@router.post(
    "",
    response_model=MachineResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_machine(machine_data: MachineCreate):
    """Register a new machine."""

    machines_collection = get_collection("machines")

    existing = await machines_collection.find_one(
        {"machine_id": machine_data.machine_id}
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Machine ID already exists",
        )

    machine_doc = machine_data.model_dump(exclude_none=True)

    machine_doc["is_active"] = True
    machine_doc["created_at"] = datetime.now(timezone.utc)
    machine_doc["updated_at"] = datetime.now(timezone.utc)

    result = await machines_collection.insert_one(machine_doc)

    # MongoDB returns ObjectId, while our API exposes string IDs.
    machine_doc["id"] = str(machine_doc.pop("_id"))
    return MachineResponse(**machine_doc)


@router.get("", response_model=MachineListResponse)
async def list_machines(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    machine_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """List machines with pagination and search."""

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

    cursor = (
        machines_collection
        .find(query)
        .sort("created_at", DESCENDING)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    items = []

    async for machine_doc in cursor:
        # Convert MongoDB ObjectId to the string expected by the API.
        # Convert MongoDB ObjectId to the string expected by the API.
        machine_doc["id"] = str(machine_doc.pop("_id"))

        assessment_count = await assessments_collection.count_documents(
            {"machine_id": machine_doc["machine_id"]}
        )

        latest_assessment = await assessments_collection.find_one(
            {"machine_id": machine_doc["machine_id"]},
            sort=[("ts", -1)],
        )

        machine = MachineResponse(
            **machine_doc,
            assessment_count=assessment_count,
        )

        if latest_assessment:
            prediction = latest_assessment.get("prediction", {})

            machine.latest_health_status = prediction.get("health_status")
            machine.latest_risk_level = prediction.get("risk_level")

            latest_id = latest_assessment.get("_id")
            machine.latest_assessment_id = (
                str(latest_id) if latest_id is not None else None
            )

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
    """Get a machine by its application-level machine_id."""

    machine_doc = await get_machine_by_id(machine_id)

    if not machine_doc:
        raise HTTPException(
            status_code=404,
            detail="Machine not found",
        )

    assessments_collection = get_collection("assessments")

    assessment_count = await assessments_collection.count_documents(
        {"machine_id": machine_id}
    )

    latest_assessment = await assessments_collection.find_one(
        {"machine_id": machine_id},
        sort=[("ts", -1)],
    )

    # Convert MongoDB ObjectId to API string ID.
    # Convert MongoDB ObjectId to API string ID.
    machine_doc["id"] = str(machine_doc.pop("_id"))
    machine = MachineResponse(
        **machine_doc,
        assessment_count=assessment_count,
    )

    if latest_assessment:
        prediction = latest_assessment.get("prediction", {})

        machine.latest_health_status = prediction.get("health_status")
        machine.latest_risk_level = prediction.get("risk_level")

        latest_id = latest_assessment.get("_id")
        machine.latest_assessment_id = (
            str(latest_id) if latest_id is not None else None
        )

    return machine


@router.patch("/{machine_id}")
async def update_machine_sensor_values(
    machine_id: str,
    update_data: MachineUpdate,
):
    """
    Update machine information.

    When sensor_values are supplied, run the existing ML model,
    save the resulting assessment, and create an alert when the
    prediction is High Risk or Critical.
    """

    from backend.model_service import predict_machine
    from backend.services.assessment import create_assessment
    from backend.services.alert import create_alert_from_assessment

    machines_collection = get_collection("machines")

    machine_doc = await get_machine_by_id(machine_id)

    if not machine_doc:
        raise HTTPException(
            status_code=404,
            detail="Machine not found",
        )

    # Build the MongoDB update document.
    update_doc = update_data.model_dump(exclude_unset=True)
    update_doc["updated_at"] = datetime.now(timezone.utc)

    # Update the in-memory copy as well so the response reflects
    # the newly supplied sensor values.
    if update_data.sensor_values is not None:
        machine_doc["sensor_values"] = update_data.sensor_values

    result = await machines_collection.find_one_and_update(
        {"machine_id": machine_id},
        {"$set": update_doc},
        return_document=True,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Machine not found",
        )

    assessment_doc = None

    if update_data.sensor_values is not None:
        sv = update_data.sensor_values

        # Run synchronous model inference in a worker thread so that
        # ML inference does not block FastAPI's async event loop.
        pred_result = await run_in_threadpool(
            predict_machine,
            product_type=sv.get("product_type", "L"),
            air_temperature=sv.get("air_temperature", 298.1),
            process_temperature=sv.get("process_temperature", 308.6),
            rotational_speed=sv.get("rotational_speed", 1450),
            torque=sv.get("torque", 45),
            tool_wear=sv.get("tool_wear", 120),
        )

        pred_result["source"] = "fastapi"

        from backend.schemas import PredictionResponse

        prediction = PredictionResponse(**pred_result)

        assessment = AssessmentCreate(
            machine_id=machine_id,
            inputs=sv,
            prediction=prediction,
            source="fastapi",
        )

        assessment_doc = await create_assessment(assessment)

        # Create an alert for High Risk or Critical predictions.
        if prediction.health_status in ("High Risk", "Critical"):
            await create_alert_from_assessment(assessment_doc)

    # Re-fetch the machine so the response includes the latest
    # # assessment count and latest health/risk information.
    fresh_machine = await get_machine_by_id(machine_id)
    if fresh_machine is None:
        raise HTTPException(
            status_code=404,
            detail="Machine not found",
        )
    assessment_count = await get_collection("assessments").count_documents(
        {"machine_id": machine_id}
    )
    latest_assessment = await get_collection("assessments").find_one(
        {"machine_id": machine_id},
        sort=[("ts", -1)],
    )
    fresh_machine["id"] = str(fresh_machine.pop("_id"))
    machine = MachineResponse(
        **fresh_machine,
        assessment_count=assessment_count,
    )
    if latest_assessment:
        prediction = latest_assessment.get("prediction", {})
        machine.latest_health_status = prediction.get("health_status")
        machine.latest_risk_level = prediction.get("risk_level")
        latest_id = latest_assessment.get("_id")
        machine.latest_assessment_id = (
            str(latest_id) if latest_id is not None else None
        )
    assessment_response = None
    if assessment_doc:
        assessment_response = AssessmentResponse.from_db(
            assessment_doc
        )
        return {
            "machine": machine,
            "assessment": assessment_response,
        }

@router.delete("/{machine_id}")
async def delete_machine(machine_id: str):
    """Delete a machine."""

    machines_collection = get_collection("machines")

    result = await machines_collection.delete_one(
        {"machine_id": machine_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Machine not found",
        )

    return {
        "message": "Machine deleted successfully"
    }