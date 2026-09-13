"""
Alert routes - simplified listing (public, no auth).
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from bson import ObjectId

from backend.models.alert import (
    AlertResponse,
    AlertListResponse,
    AlertListQuery,
    AlertSeverity,
    AlertInDB,
)
from backend.db.mongodb import get_collection


router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(query: AlertListQuery = Query()):
    """List alerts with filters and pagination (public)."""
    alerts_collection = get_collection("alerts")

    q = {}
    if query.machine_id:
        q["machine_id"] = query.machine_id
    if query.severity:
        q["severity"] = query.severity.value
    if query.date_from or query.date_to:
        date_q = {}
        if query.date_from:
            date_q["$gte"] = query.date_from
        if query.date_to:
            date_q["$lte"] = query.date_to
        q["ts"] = date_q

    total = await alerts_collection.count_documents(q)
    total_pages = (total + query.page_size - 1) // query.page_size

    cursor = alerts_collection.find(q).sort("ts", -1).skip((query.page - 1) * query.page_size).limit(query.page_size)

    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        alert = AlertInDB(**doc)
        items.append(AlertResponse.from_db(alert))

    return AlertListResponse(
        items=items,
        total=total,
        page=query.page,
        page_size=query.page_size,
        total_pages=total_pages,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str):
    """Get a single alert by ID (public)."""
    doc = await get_collection("alerts").find_one({"_id": ObjectId(alert_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Alert not found")

    doc["_id"] = str(doc["_id"])
    alert = AlertInDB(**doc)
    return AlertResponse.from_db(alert)
