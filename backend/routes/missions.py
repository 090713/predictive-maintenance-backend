"""
Mission routes - CRUD operations for missions.
"""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from backend.config import settings
from backend.models.mission import MissionCreate, MissionUpdate, MissionResponse, MissionListResponse
from backend.models.user import UserResponse, UserRole
from backend.services.auth import get_current_user, require_admin, require_supervisor_or_admin, get_current_user_response
from backend.db.mongodb import get_collection


router = APIRouter(prefix="/api/v1/missions", tags=["Missions"])


async def get_mission_by_id(mission_id: str) -> Optional[dict]:
    """Get mission by mission_id string."""
    missions_collection = get_collection("missions")
    return await missions_collection.find_one({"mission_id": mission_id})


async def get_mission_by_object_id(oid: str) -> Optional[dict]:
    """Get mission by ObjectId string."""
    missions_collection = get_collection("missions")
    return await missions_collection.find_one({"_id": ObjectId(oid)})


@router.post("", response_model=MissionResponse, status_code=status.HTTP_201_CREATED)
async def create_mission(
    mission_data: MissionCreate,
    current_user: UserResponse = Depends(require_admin)
):
    """Create a new mission (admin only)."""
    missions_collection = get_collection("missions")

    # Check if mission_id already exists
    existing = await missions_collection.find_one({"mission_id": mission_data.mission_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mission ID already exists",
        )

    mission_doc = mission_data.model_dump()
    mission_doc["assigned_worker_ids"] = []
    mission_doc["created_at"] = datetime.now(timezone.utc)
    mission_doc["updated_at"] = datetime.now(timezone.utc)

    result = await missions_collection.insert_one(mission_doc)
    mission_doc["_id"] = str(result.inserted_id)

    return MissionResponse.from_db(MissionResponse(**mission_doc), machine_count=0)


@router.get("", response_model=MissionListResponse)
async def list_missions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user_response)
):
    """List missions with pagination and search."""
    missions_collection = get_collection("missions")
    machines_collection = get_collection("machines")

    # Build query based on role
    query = {}
    if current_user.role == UserRole.WORKER:
        query["assigned_worker_ids"] = current_user.id

    if search:
        query["$text"] = {"$search": search}

    # Get total count
    total = await missions_collection.count_documents(query)
    total_pages = (total + page_size - 1) // page_size

    # Get missions
    cursor = missions_collection.find(query).sort("created_at", DESCENDING).skip((page - 1) * page_size).limit(page_size)

    items = []
    async for mission_doc in cursor:
        mission_doc["_id"] = str(mission_doc["_id"])
        # Count machines for this mission
        machine_count = await machines_collection.count_documents({"mission_id": mission_doc["mission_id"]})
        mission = MissionResponse.from_db(MissionResponse(**mission_doc), machine_count=machine_count)
        items.append(mission)

    return MissionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{mission_id}", response_model=MissionResponse)
async def get_mission(
    mission_id: str,
    current_user: UserResponse = Depends(get_current_user_response)
):
    """Get a mission by ID."""
    mission_doc = await get_mission_by_id(mission_id)
    if not mission_doc:
        raise HTTPException(status_code=404, detail="Mission not found")

    # Check access for workers
    if current_user.role == UserRole.WORKER:
        if current_user.id not in mission_doc.get("assigned_worker_ids", []):
            raise HTTPException(status_code=403, detail="Access denied")

    machines_collection = get_collection("machines")
    machine_count = await machines_collection.count_documents({"mission_id": mission_id})

    mission_doc["_id"] = str(mission_doc["_id"])
    return MissionResponse.from_db(MissionResponse(**mission_doc), machine_count=machine_count)


@router.patch("/{mission_id}", response_model=MissionResponse)
async def update_mission(
    mission_id: str,
    update_data: dict,
    current_user: UserResponse = Depends(require_admin)
):
    """Update a mission (admin only)."""
    missions_collection = get_collection("missions")

    mission_doc = await get_mission_by_id(mission_id)
    if not mission_doc:
        raise HTTPException(status_code=404, detail="Mission not found")

    # Update allowed fields
    allowed_fields = {"name", "type", "description"}
    update_doc = {k: v for k, v in update_data.items() if k in allowed_fields}
    if not update_doc:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    update_doc["updated_at"] = datetime.now(timezone.utc)

    result = await missions_collection.find_one_and_update(
        {"mission_id": mission_id},
        {"$set": update_doc},
        return_document=True
    )

    if not result:
        raise HTTPException(status_code=404, detail="Mission not found")

    result["_id"] = str(result["_id"])
    return MissionResponse.from_db(MissionResponse(**result))


@router.delete("/{mission_id}")
async def delete_mission(
    mission_id: str,
    current_user: UserResponse = Depends(require_admin)
):
    """Delete a mission (admin only)."""
    missions_collection = get_collection("missions")
    machines_collection = get_collection("machines")

    # Check if mission has machines
    machine_count = await machines_collection.count_documents({"mission_id": mission_id})
    if machine_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete mission with {machine_count} machines. Reassign or delete machines first."
        )

    result = await missions_collection.delete_one({"mission_id": mission_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Mission not found")

    return {"message": "Mission deleted successfully"}


@router.post("/{mission_id}/assign-workers", response_model=MissionResponse)
async def assign_workers_to_mission(
    mission_id: str,
    worker_ids: List[str],
    current_user: UserResponse = Depends(require_supervisor_or_admin)
):
    """Assign workers to a mission (admin/supervisor)."""
    missions_collection = get_collection("missions")
    users_collection = get_collection("users")

    mission_doc = await get_mission_by_id(mission_id)
    if not mission_doc:
        raise HTTPException(status_code=404, detail="Mission not found")

    # Validate workers exist and have worker role
    if worker_ids:
        workers = await users_collection.find({
            "_id": {"$in": [ObjectId(wid) for wid in worker_ids]},
            "role": UserRole.WORKER.value
        }).to_list(length=None)

        if len(workers) != len(worker_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more worker IDs are invalid or not workers"
            )

    # Update mission
    result = await missions_collection.find_one_and_update(
        {"mission_id": mission_id},
        {"$set": {"assigned_worker_ids": worker_ids, "updated_at": datetime.now(timezone.utc)}},
        return_document=True
    )

    # Update workers' assigned missions
    await users_collection.update_many(
        {"_id": {"$in": [ObjectId(wid) for wid in worker_ids]}},
        {"$addToSet": {"assigned_mission_ids": mission_id}}
    )

    # Remove mission from workers no longer assigned
    old_worker_ids = mission_doc.get("assigned_worker_ids", [])
    removed_workers = set(old_worker_ids) - set(worker_ids)
    if removed_workers:
        await users_collection.update_many(
            {"_id": {"$in": [ObjectId(wid) for wid in removed_workers]}},
            {"$pull": {"assigned_mission_ids": mission_id}}
        )

    result["_id"] = str(result["_id"])
    return MissionResponse.from_db(MissionResponse(**result))