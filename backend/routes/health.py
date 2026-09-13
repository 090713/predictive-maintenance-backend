"""
Health check and system info routes.
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends
from pymongo import ASCENDING

from backend.config import settings
from backend.db.mongodb import get_collection, MongoDB
from backend.model_service import MAIN_MODEL_PATH, ANOMALY_MODEL_PATH, FAILURE_MODE_MODEL_PATH


router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "message": "Predictive Maintenance backend is running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including database and models."""
    checks = {}

    # Database check
    try:
        await MongoDB.client.admin.command("ping")
        checks["database"] = {"status": "healthy", "message": "Connected to MongoDB"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "message": str(e)}

    # Models check
    try:
        models_exist = all([
            MAIN_MODEL_PATH.exists(),
            ANOMALY_MODEL_PATH.exists(),
            FAILURE_MODE_MODEL_PATH.exists(),
        ])
        checks["models"] = {
            "status": "healthy" if models_exist else "unhealthy",
            "message": "Models loaded" if models_exist else "Model files missing",
            "paths": {
                "main": str(MAIN_MODEL_PATH),
                "anomaly": str(ANOMALY_MODEL_PATH),
                "failure_mode": str(FAILURE_MODE_MODEL_PATH),
            }
        }
    except Exception as e:
        checks["models"] = {"status": "unhealthy", "message": str(e)}

    # Gradio fallback check
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.GRADIO_API_URL}/health", timeout=5.0)
            checks["gradio_fallback"] = {
                "status": "healthy" if resp.status_code == 200 else "degraded",
                "message": f"Gradio API responded with {resp.status_code}",
            }
    except Exception:
        checks["gradio_fallback"] = {
            "status": "unavailable",
            "message": "Gradio fallback unreachable",
        }

    overall_status = "healthy" if all(c["status"] == "healthy" for c in checks.values()) else "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
        "checks": checks,
    }


@router.get("/version")
async def version_info():
    """Get version and model info."""
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "model_version": "1.0.0",  # Would come from model metadata
        "api_version": "v1",
    }