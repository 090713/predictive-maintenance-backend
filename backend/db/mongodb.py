"""
MongoDB connection management using Motor (async driver).
Provides database instance and collection access with proper indexing.
"""
from contextlib import asynccontextmanager
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING, TEXT
from pymongo.errors import CollectionInvalid

from backend.config import settings


class MongoDB:
    """MongoDB connection manager."""

    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls) -> None:
        """Initialize MongoDB connection."""
        if cls.client is not None:
            return

        cls.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            maxPoolSize=50,
            minPoolSize=10,
            maxIdleTimeMS=30000,
            waitQueueTimeoutMS=5000,
            serverSelectionTimeoutMS=10000,
        )
        cls.database = cls.client[settings.MONGODB_DATABASE]

        # Verify connection
        await cls.client.admin.command("ping")
        print(f"Connected to MongoDB: {settings.MONGODB_DATABASE}")

        # Create indexes
        await cls.create_indexes()

    @classmethod
    async def close(cls) -> None:
        """Close MongoDB connection."""
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.database = None
            print("MongoDB connection closed")

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if cls.database is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return cls.database

    @classmethod
    def get_collection(cls, name: str) -> AsyncIOMotorCollection:
        """Get collection by name."""
        return cls.get_database()[name]

    @classmethod
    async def create_indexes(cls) -> None:
        """Create all required indexes for collections."""
        db = cls.get_database()

        # Users collection indexes
        users = db["users"]
        await users.create_index([("email", ASCENDING)], unique=True)
        await users.create_index([("role", ASCENDING)])
        await users.create_index([("assigned_mission_ids", ASCENDING)])

        # Missions collection indexes
        missions = db["missions"]
        await missions.create_index([("mission_id", ASCENDING)], unique=True)
        await missions.create_index([("name", TEXT)])
        await missions.create_index([("created_at", DESCENDING)])

        # Machines collection indexes
        machines = db["machines"]
        await machines.create_index([("machine_id", ASCENDING)], unique=True)
        await machines.create_index([("mission_id", ASCENDING)])
        await machines.create_index([("assigned_worker_ids", ASCENDING)])
        await machines.create_index([("type", ASCENDING)])

        # Assessments collection indexes
        assessments = db["assessments"]
        await assessments.create_index([("machine_id", ASCENDING)])
        await assessments.create_index([("mission_id", ASCENDING)])
        await assessments.create_index([("user_id", ASCENDING)])
        await assessments.create_index([("ts", DESCENDING)])
        await assessments.create_index([("health_status", ASCENDING)])
        await assessments.create_index([("risk_level", ASCENDING)])
        await assessments.create_index(
            [("mission_id", ASCENDING), ("ts", DESCENDING)]
        )

        # Alerts collection indexes
        alerts = db["alerts"]
        await alerts.create_index([("assessment_id", ASCENDING)], unique=True)
        await alerts.create_index([("machine_id", ASCENDING)])
        await alerts.create_index([("mission_id", ASCENDING)])
        await alerts.create_index([("status", ASCENDING)])
        await alerts.create_index([("severity", ASCENDING)])
        await alerts.create_index([("ts", DESCENDING)])

        # Reports collection indexes
        reports = db["reports"]
        await reports.create_index([("requested_by", ASCENDING)])
        await reports.create_index([("status", ASCENDING)])
        await reports.create_index([("created_at", DESCENDING)])
        await reports.create_index([("mission_ids", ASCENDING)])
        await reports.create_index([("machine_ids", ASCENDING)])

        print("MongoDB indexes created")


@asynccontextmanager
async def lifespan_mongodb():
    """FastAPI lifespan context manager for MongoDB."""
    await MongoDB.connect()
    try:
        yield
    finally:
        await MongoDB.close()


def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency for database access."""
    return MongoDB.get_database()


def get_collection(name: str) -> AsyncIOMotorCollection:
    """FastAPI dependency for collection access."""
    return MongoDB.get_collection(name)