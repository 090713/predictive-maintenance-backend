"""
Assessment routes - prediction history and listing (public, no auth).
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId

from backend.config import settings
from backend.models.assessment import (
    AssessmentCreate, AssessmentResponse, AssessmentDetailResponse,
    AssessmentInDB, AssessmentListQuery, AssessmentListResponse,
)
from backend.schemas import MachineInput, PredictionResponse
from backend.model_service import predict_machine
from backend.db.mongodb import get_collection
import httpx


router = APIRouter(prefix="/api/v1/assessments", tags=["Assessments"])


GRADIO_API_URL = settings.GRADIO_API_URL


async def call_gradio_fallback(machine_input: MachineInput) -> Optional[PredictionResponse]:
    """Call Gradio API as fallback."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            post_resp = await client.post(
                f"{GRADIO_API_URL}/call/assess",
                json={
                    "data": [
                        machine_input.product_type,
                        machine_input.air_temperature,
                        machine_input.process_temperature,
                        machine_input.rotational_speed,
                        machine_input.torque,
                        machine_input.tool_wear,
                        machine_input.machine_id or "UNKNOWN",
                        machine_input.state or "RUNNING",
                    ]
                },
            )
            post_resp.raise_for_status()
            event_id = post_resp.json().get("event_id")
            if not event_id:
                return None

            async with client.stream(
                "GET",
                f"{GRADIO_API_URL}/call/assess/{event_id}",
                headers={"Accept": "text/event-stream"},
                timeout=60.0,
            ) as stream_resp:
                async for line in stream_resp.aiter_lines():
                    if line.startswith("event: complete"):
                        continue
                    if line.startswith("data: "):
                        import json
                        data = json.loads(line[6:])
                        if isinstance(data, list) and data:
                            return parse_gradio_output(data)
    except Exception:
        pass
    return None


def parse_gradio_output(outputs: list) -> PredictionResponse:
    """Parse Gradio outputs into PredictionResponse."""
    full = outputs[-1] if isinstance(outputs[-1], dict) else {}

    failure_prob = full.get("failure_probability", 0)
    if isinstance(failure_prob, str) and failure_prob.endswith("%"):
        failure_prob = float(failure_prob.rstrip("%")) / 100

    return PredictionResponse(
        failure_probability=failure_prob,
        predicted_failure=failure_prob >= 0.5,
        anomaly_score=full.get("anomaly_score", 0),
        anomaly_percentile=full.get("anomaly_percentile", 0),
        is_anomaly=full.get("is_anomaly", False),
        failure_modes=full.get("failure_modes", {}),
        health_status=full.get("health_status", "Normal"),
        failure_mode=full.get("failure_mode"),
        failure_mode_name=full.get("failure_mode_name"),
        explanation=full.get("explanation", ""),
        maintenance_recommendation=full.get("recommended_maintenance_action", ""),
        predicted_class=full.get("predicted_class", "UNKNOWN"),
        recommended_maintenance_action=full.get("recommended_maintenance_action", ""),
        decision_threshold=full.get("decision_threshold", 0.5),
        risk_level=full.get("risk_level", "Low"),
        urgency=full.get("urgency", "Routine"),
        likely_failure_modes=full.get("likely_failure_modes", []),
        contributing_features=full.get("contributing_features", []),
        condition_evidence=full.get("condition_evidence", []),
        model_version=full.get("model_version", "gradio-fallback"),
        prediction_id=full.get("prediction_id", ""),
        prediction_timestamp=datetime.now(timezone.utc).isoformat(),
        latency_ms=full.get("latency_ms", 0),
        decision_support_notice="Fallback: Gradio API (results may differ from primary)",
    )


async def call_simulated_fallback(machine_input: MachineInput) -> PredictionResponse:
    """Use the deterministic simulated engine as final fallback."""
    from backend.services.fallback import simulate_assessment
    return simulate_assessment(machine_input)


@router.post("/predict", response_model=PredictionResponse)
async def predict(machine: MachineInput):
    """
    Primary prediction endpoint (public).
    Tries FastAPI model -> Gradio fallback -> Simulated fallback.
    Persists assessment to MongoDB.
    """
    from backend.services.assessment import create_assessment
    from backend.services.alert import create_alert_from_assessment

    # Try primary FastAPI model
    try:
        result = predict_machine(
            product_type=machine.product_type,
            air_temperature=machine.air_temperature,
            process_temperature=machine.process_temperature,
            rotational_speed=machine.rotational_speed,
            torque=machine.torque,
            tool_wear=machine.tool_wear,
        )
        result["source"] = "fastapi"
    except Exception:
        # Try Gradio fallback
        gradio_result = await call_gradio_fallback(machine)
        if gradio_result:
            result = gradio_result
            result.source = "gradio"
        else:
            # Final simulated fallback
            result = await call_simulated_fallback(machine)
            result.source = "simulated"

    # Create assessment record
    assessment = AssessmentCreate(
        machine_id=machine.machine_id,
        inputs=machine.model_dump(exclude_none=True),
        prediction=PredictionResponse(**result),
        source=result.get("source", "fastapi"),
    )

    assessment_doc = await create_assessment(assessment)

    # Auto-create alert if high risk
    health_status = result.get("health_status", "")
    if health_status in ("High Risk", "Critical"):
        await create_alert_from_assessment(assessment_doc)

    return PredictionResponse(**result)


@router.get("", response_model=AssessmentListResponse)
async def list_assessments(query: AssessmentListQuery = Depends()):
    """List assessments with filters and pagination (public)."""
    assessments_collection = get_collection("assessments")

    # Build query
    q = {}
    if query.machine_id:
        q["machine_id"] = query.machine_id
    if query.health_status:
        q["prediction.health_status"] = query.health_status
    if query.risk_level:
        q["prediction.risk_level"] = query.risk_level
    if query.date_from or query.date_to:
        date_q = {}
        if query.date_from:
            date_q["$gte"] = query.date_from
        if query.date_to:
            date_q["$lte"] = query.date_to
        q["ts"] = date_q

    total = await assessments_collection.count_documents(q)
    total_pages = (total + query.page_size - 1) // query.page_size

    cursor = assessments_collection.find(q).sort("ts", -1).skip((query.page - 1) * query.page_size).limit(query.page_size)

    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(AssessmentResponse.from_db(AssessmentInDB(**doc)))

    return AssessmentListResponse(
        items=items,
        total=total,
        page=query.page,
        page_size=query.page_size,
        total_pages=total_pages,
    )


@router.get("/{assessment_id}", response_model=AssessmentDetailResponse)
async def get_assessment(assessment_id: str):
    """Get a single assessment by ID (public)."""
    doc = await get_collection("assessments").find_one({"_id": ObjectId(assessment_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Assessment not found")

    doc["_id"] = str(doc["_id"])
    return AssessmentDetailResponse(**doc)
