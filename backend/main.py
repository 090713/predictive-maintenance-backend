"""
FastAPI Backend
---------------
Main entry point for the Predictive Maintenance Agent.

Responsibilities:
1. Start the FastAPI application
2. Provide health-check endpoints
3. Receive machine sensor data
4. Validate the input
5. Call the ML service
6. Return the combined prediction to the frontend
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.db.mongodb import MongoDB, lifespan_mongodb
from backend.routes import machines, assessments, alerts, health
from backend.schemas import MachineInput, PredictionResponse
from backend.model_service import predict_machine


# =========================================================
# APPLICATION LIFESPAN
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    # A database outage must NOT take the whole API down. If MongoDB is
    # unreachable (wrong/missing MONGODB_URI env, cluster down, restart),
    # log the failure and boot in a degraded state so the app can still
    # answer health checks and surface the exact DB error instead of
    # crashing at startup (which manifests as a Railway 502 for all routes).
    try:
        await MongoDB.connect()
    except Exception as exc:  # noqa: BLE001 - boot must survive any DB error
        print(f"WARNING: MongoDB connection failed at startup: {exc!r}")
        print("Degraded mode: /health and /health/detailed will report DB status")
    try:
        yield
    finally:
        # Shutdown
        await MongoDB.close()


# =========================================================
# CREATE FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Backend API for the manufacturing "
        "predictive maintenance agent"
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
)


# =========================================================
# CORS CONFIGURATION
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROUTE REGISTRATION
# =========================================================

# Health & System
app.include_router(health.router, tags=["Health"])

# Core Resources
app.include_router(machines.router, tags=["Machines"])

# Predictions & Monitoring
app.include_router(assessments.router, tags=["Assessments"])
app.include_router(alerts.router, tags=["Alerts"])


# =========================================================
# LEGACY PREDICT ENDPOINT (for backward compatibility)
# =========================================================

@app.post(
    "/v1/predict",
    response_model=PredictionResponse,
    include_in_schema=False,  # Hidden from OpenAPI, use /api/v1/assessments/predict instead
)
def predict_legacy(machine: MachineInput):
    """
    Legacy predict endpoint for backward compatibility.
    Use POST /api/v1/assessments/predict for new implementations.
    """
    result = predict_machine(
        product_type=machine.product_type,
        air_temperature=machine.air_temperature,
        process_temperature=machine.process_temperature,
        rotational_speed=machine.rotational_speed,
        torque=machine.torque,
        tool_wear=machine.tool_wear
    )
    return result
