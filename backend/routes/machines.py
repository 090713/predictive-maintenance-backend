"""
Machine routes - CRUD operations for machines.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from backend.config import settings
from backend.models.machine import MachineCreate, MachineUpdate, MachineResponse, MachineListResponse, MachineAssignWorkersRequest
from backend.models.user import UserResponse, UserRole
from backend.services.auth import get_current_user, require_admin, require_supervisor_or_admin, get_current_user_response
from backend.db.mongodb import get_collection


router = APIRouter(prefix="/api/v1/machines", tags=["Machines"])


async def get_machine_by_id(machine_id: str) -> Optional[dict]:
    """Get machine by machine_id string."""
    machines_collection = get_collection("machines")
    return await machines_collection.find_one({"machine_id": machine_id})


async def get_machine_by_object_id(oid: str) -> Optional[dict]:
    """Get machine by ObjectId string."""
    machines_collection = get_collection("machines")
    return await machines_collection.find_one({"_id": ObjectId(oid)})


@router.post("", response_model=MachineResponse, status_code=status.HTTP_201_CREATED)
async def create_machine(
    machine_data: MachineCreate,
    current_user: UserResponse = Depends(require_admin)
):
    """Create a new machine (admin only)."""
    machines_collection = get_collection("machines")
    missions_collection = get_collection("missions")

    # Validate mission exists
    mission = await missions_collection.find_one({"mission_id": machine_data.mission_id})
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    # Check if machine_id already exists
    existing = await machines_collection.find_one({"machine_id": machine_data.machine_id})
    if existing:
        raise HTTPException(status_code=400, detail="Machine ID already exists")

    machine_doc = machine_data.model_dump()
    machine_doc["assigned_worker_ids"] = []
    machine_doc["created_at"] = datetime.now(timezone.utc)
    machine_doc["updated_at"] = datetime.now(timezone.utc)

    result = await machines_collection.insert_one(machine_doc)
    machine_doc["_id"] = str(result.inserted_id)

    return MachineResponse.from_db(MachineResponse(**machine_doc))


@router.get("", response_model=MachineListResponse)
async def list_machines(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mission_id: Optional[str] = Query(None),
    machine_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user_response)
):
    """List machines with pagination, filters, and search."""
    machines_collection = get_collection("machines")
    assessments_collection = get_collection("assessments")

    # Build query based on role
    query = {}
    if current_user.role == UserRole.WORKER:
        query["assigned_worker_ids"] = current_user.id

    if mission_id:
        query["mission_id"] = mission_id
    if machine_type:
        query["type"] = machine_type
    if search:
        query["$or"] = [
            {"machine_id": {"$regex": search, "$options": "i"}},
            {"type": {"$regex": search, "$options": "i"}},
            {"location": {"$regex": search, "$options": "i"}},
        ]

    # Get total count
    total = await machines_collection.count_documents(query)
    total_pages = (total + page_size - 1) // page_size

    # Get machines
    cursor = machines_collection.find(query).sort("created_at", DESCENDING).skip((page - 1) * page_size).limit(page_size)

    items = []
    async for machine_doc in cursor:
        machine_doc["_id"] = str(machine_doc["_id"])
        # Get assessment count and latest health
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
        items.append(machine)

    return MachineListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{machine_id}", response_model=MachineResponse)
async def get_machine(
    machine_id: str,
    current_user: UserResponse = Depends(get_current_user_response)
):
    """Get a machine by ID."""
    machine_doc = await get_machine_by_id(machine_id)
    if not machine_doc:
        raise HTTPException(status_code=404, detail="Machine not found")

    # Check access for workers
    if current_user.role == UserRole.WORKER:
        if current_user.id not in machine_doc.get("assigned_worker_ids", []):
            raise HTTPException(status_code=403, detail="Access denied")

    machines_collection = get_collection("machines")
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

    return machine


@router.patch("/{machine_id}", response_model=MachineResponse)
async def update_machine(
    machine_id: str,
    update_data: MachineUpdate,
    current_user: UserResponse = Depends(require_admin)
):
    """Update a machine (admin only)."""
    machines_collection = get_collection("machines")
    missions_collection = get_collection("missions")

    machine_doc = await get_machine_by_id(machine_id)
    if not machine_doc:
        raise HTTPException(status_code=404, detail="Machine not found")

    # Validate mission if provided
    if update_data.mission_id:
        mission = await missions_collection.find_one({"mission_id": update_data.mission_id})
        if not mission:
            raise HTTPException(status_code=404, detail="Mission not found")

    # Prepare update document
    update_doc = update_data.model_dump(exclude_unset=True)
    update_doc["updated_at"] = datetime.now(timezone.utc)

    # Validate workers if provided
    if "assigned_worker_ids" in update_doc:
        users_collection = get_collection("users")
        worker_ids = update_doc["assigned_worker_ids"]
        if worker_ids:
            workers = await users_collection.find({
                "_id": {"$in": [ObjectId(wid) for wid in worker_ids]},
                "role": "worker"
            }).to_list(length=None)
            if len(workers) != len(worker_ids):
                raise HTTPException(status_code=400, detail="One or more worker IDs are invalid")

    result = await machines_collection.find_one_and_update(
        {"machine_id": machine_id},
        {"$set": update_doc},
        return_document=True
    )

    if not result:
        raise HTTPException(status_code=404, detail="Machine not found")

    result["_id"] = str(result["_id"])
    return MachineResponse.from_db(MachineResponse(**result))


@router.delete("/{machine_id}")
async def delete_machine(
    machine_id: str,
    current_user: UserResponse = Depends(require_admin)
):
    """Delete a machine (admin only)."""
    machines_collection = get_collection("machines")
    result = await machines_collection.delete_one({"machine_id": machine_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Machine not found")
    return {"message": "Machine deleted successfully"}


@router.post("/{machine_id}/assign-workers", response_model=MachineResponse)
async def assign_workers_to_machine(
    machine_id: str,
    request: MachineAssignWorkersRequest,
    current_user: UserResponse = Depends(require_supervisor_or_admin)
):
    """Assign workers to a machine (admin/supervisor)."""
    machines_collection = get_collection("machines")
    users_collection = get_collection("users")

    machine_doc = await get_machine_by_id(machine_id)
    if not machine_doc:
        raise HTTPException(status_code=404, detail="Machine not found")

    # Validate workers
    worker_ids = request.worker_ids
    if worker_ids:
        workers = await users_collection.find({
            "_id": {"$in": [ObjectId(wid) for wid in worker_ids]},
            "role": "worker"
        }).to_list(length=None)
        if len(workers) != len(worker_ids):
            raise HTTPException(status_code=400, detail="One or more worker IDs are invalid")

    # Update machine
    result = await machines_collection.find_one_and_update(
        {"machine_id": machine_id},
        {"$set": {"assigned_worker_ids": worker_ids, "updated_at": datetime.now(timezone.utc)}},
        return_document=True
    )

    # Update workers' assigned machines (via missions)
    missions_collection = get_collection("missions")
    mission = await missions_collection.find_one({"mission_id": machine_doc["mission_id"]})
    if mission:
        mission_id = mission["mission_id"]
        await users_collection.update_many(
            {"_id": {"$in": [ObjectId(wid) for wid in worker_ids]}},
            {"$addToSet": {"assigned_mission_ids": mission_id}}
        )

    result["_id"] = str(result["_id"])
    return MachineResponse.from_db(MachineResponse(**result))