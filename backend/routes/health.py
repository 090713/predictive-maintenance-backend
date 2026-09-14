"""
Health check and system information routes.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from backend.config import settings
from backend.db.mongodb import MongoDB
from backend.model_service import (
    MAIN_MODEL_PATH,
    ANOMALY_MODEL_PATH,
    FAILURE_MODE_MODEL_PATH,
)


router = APIRouter(
    prefix="/api/v1",
    tags=["Health"],
)


@router.get("/health")
async def health_check():
    """Basic health check for the API."""

    return {
        "status": "healthy",
        "message": "Predictive Maintenance backend is running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check for database and ML model availability.

    Internal exception details and server filesystem paths are deliberately
    not returned to the client.
    """

    checks = {}

    # ---------------------------------------------------------
    # Database check
    # ---------------------------------------------------------
    try:
        await MongoDB.client.admin.command("ping")

        checks["database"] = {
            "status": "healthy",
            "message": "Connected to MongoDB",
        }

    except Exception:
        # Do not expose the raw database exception to the public API.
        checks["database"] = {
            "status": "unhealthy",
            "message": "Database connection unavailable",
        }

    # ---------------------------------------------------------
    # ML model check
    # ---------------------------------------------------------
    try:
        models_exist = all(
            [
                MAIN_MODEL_PATH.exists(),
                ANOMALY_MODEL_PATH.exists(),
                FAILURE_MODE_MODEL_PATH.exists(),
            ]
        )

        checks["models"] = {
            "status": "healthy" if models_exist else "unhealthy",
            "message": (
                "Models loaded"
                if models_exist
                else "One or more model files are missing"
            ),
        }

    except Exception:
        # Do not expose filesystem or internal model-loading details.
        checks["models"] = {
            "status": "unhealthy",
            "message": "Unable to verify model availability",
        }

    overall_status = (
        "healthy"
        if all(
            check["status"] == "healthy"
            for check in checks.values()
        )
        else "degraded"
    )

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
        "checks": checks,
    }


@router.get("/version")
async def version_info():
    """Return public application and API version information."""

    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "model_version": "1.0.0",
        "api_version": "v1",
    }