"""
Alert routes - alert listing, acknowledgment, resolution.
"""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from backend.config import settings
from backend.models.alert import AlertResponse, AlertListResponse, AlertListQuery, AlertActionRequest
from backend.models.user import UserResponse, UserRole
from backend.services.auth import get_current_user_response
from backend.db.mongodb import get_collection


router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    query: AlertListQuery = Depends(),
    current_user: UserResponse = Depends(get_current_user_response)
):
    """List alerts with filters and pagination."""
    alerts_collection = get_collection("alerts")

    # Build query based on role
    query = {}
    if current_user.role == "worker":
        # Workers see alerts for their assigned machines
        machines_collection = get_collection("machines")
        user_machines = await machines_collection.find(
            {"assigned_worker_ids": current_user.id}
        ).to_list(length=None)
        machine_ids = [m["machine_id"] for m in user_machines]
        query["machine_id"] = {"$in": machine_ids}

    if query.mission_id:
        query["mission_id"] = query.mission_id
    if query.machine_id:
        query["machine_id"] = query.machine_id
    if query.status:
        query["status"] = query.status.value
    if query.severity:
        query["severity"] = query.severity.value
    if query.date_from or query.date_to:
        date_query = {}
        if query.date_from:
            date_query["$gte"] = query.date_from
        if query.date_to:
            date_query["$lte"] = query.date_to
        query["ts"] = date_query

    # Get total count
    total = await alerts_collection.count_documents(query)
    total_pages = (total + query.page_size - 1) // query.page_size

    # Get alerts
    cursor = alerts_collection.find(query).sort("ts", -1).skip((query.page - 1) * query.page_size).limit(query.page_size)

    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(AlertResponse.from_db(doc))

    return AlertListResponse(
        items=items,
        total=total,
        page=query.page,
        page_size=query.page_size,
        total_pages=total_pages,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    current_user: UserResponse = Depends(get_current_user_response)
):
    """Get a single alert by ID."""
    doc = await get_collection("alerts").find_one({"_id": ObjectId(alert_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Check access for workers
    if current_user.role == "worker":
        machines_collection = get_collection("machines")
        machine = await machines_collection.find_one({"machine_id": doc["machine_id"]})
        if not machine or current_user.id not in machine.get("assigned_worker_ids", []):
            raise HTTPException(status_code=403, detail="Access denied")

    doc["_id"] = str(doc["_id"])
    return AlertResponse.from_db(doc)


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    request: AlertActionRequest,
    current_user: UserResponse = Depends(get_current_user_response)
):
    """Acknowledge an alert (supervisor+ or assigned worker)."""
    alerts_collection = get_collection("alerts")

    doc = await alerts_collection.find_one({"_id": ObjectId(alert_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Check permissions
    if current_user.role == "worker":
        machines_collection = get_collection("machines")
        machine = await machines_collection.find_one({"machine_id": doc["machine_id"]})
        if not machine or current_user.id not in machine.get("assigned_worker_ids", []):
            raise HTTPException(status_code=403, detail="Not authorized for this machine")

    if doc["status"] != "Open":
        raise HTTPException(status_code=400, detail="Alert is not open")

    result = await alerts_collection.find_one_and_update(
        {"_id": ObjectId(alert_id)},
        {"$set": {
            "status": "Acknowledged",
            "acknowledged_by": current_user.id,
            "acknowledged_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }},
        return_document=True
    )

    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")

    result["_id"] = str(result["_id"])
    return AlertResponse.from_db(result)


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    request: AlertActionRequest,
    current_user: UserResponse = Depends(get_current_user_response)
):
    """Resolve an alert (supervisor+)."""
    if current_user.role not in ("admin", "supervisor"):
        raise HTTPException(status_code=403, detail="Only supervisors and admins can resolve alerts")

    alerts_collection = get_collection("alerts")

    doc = await alerts_collection.find_one({"_id": ObjectId(alert_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Alert not found")

    if doc["status"] == "Resolved":
        raise HTTPException(status_code=400, detail="Alert already resolved")

    result = await alerts_collection.find_one_and_update(
        {"_id": ObjectId(alert_id)},
        {"$set": {
            "status": "Resolved",
            "resolved_by": current_user.id,
            "resolved_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }},
        return_document=True
    )

    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")

    result["_id"] = str(result["_id"])
    return AlertResponse.from_db(result)