"""
Assessment service - persistence and querying.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from bson import ObjectId

from backend.models.assessment import AssessmentCreate, AssessmentInDB
from backend.db.mongodb import get_collection


async def create_assessment(assessment: AssessmentCreate) -> AssessmentInDB:
    """Create a new assessment record."""
    assessments_collection = get_collection("assessments")

    doc = assessment.model_dump()
    doc["ts"] = datetime.now(timezone.utc)

    result = await assessments_collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    return AssessmentInDB(**doc)


async def get_assessment(assessment_id: str) -> Optional[AssessmentInDB]:
    """Get assessment by ID."""
    doc = await get_collection("assessments").find_one({"_id": ObjectId(assessment_id)})
    if doc:
        doc["_id"] = str(doc["_id"])
        return AssessmentInDB(**doc)
    return None


async def list_assessments(
    query: dict,
    page: int = 1,
    page_size: int = 20,
    sort_field: str = "ts",
    sort_order: int = -1,
) -> tuple[List[AssessmentInDB], int]:
    """List assessments with pagination."""
    assessments_collection = get_collection("assessments")

    total = await assessments_collection.count_documents(query)
    cursor = assessments_collection.find(query).sort(sort_field, sort_order).skip((page - 1) * page_size).limit(page_size)

    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(AssessmentInDB(**doc))

    return items, total