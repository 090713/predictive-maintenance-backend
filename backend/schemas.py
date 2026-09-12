# schemas.py
# ---------------------------------------------------------
# This file defines the input and output formats of our API.
#
# MachineInput:
#   Data that the frontend sends to the backend.
#
# PredictionResponse:
#   Data that the backend sends back to the frontend.
# ---------------------------------------------------------

from typing import Dict, Optional, Literal

from pydantic import BaseModel


# ---------------------------------------------------------
# INPUT SCHEMA
# ---------------------------------------------------------
# These are the 6 raw values expected from the frontend.
#
# The ML teammate's model expects exactly these fields.
# ---------------------------------------------------------

class MachineInput(BaseModel):

    # Product type of the machine: Low, Medium, or High
    product_type: Literal["L", "M", "H"]

    # Air temperature in Kelvin
    air_temperature: float

    # Process temperature in Kelvin
    process_temperature: float

    # Machine rotational speed in RPM
    rotational_speed: float

    # Machine torque in Newton-metres
    torque: float

    # Tool wear in minutes
    tool_wear: float


# ---------------------------------------------------------
# OUTPUT SCHEMA
# ---------------------------------------------------------
# These are the results returned by our predictive
# maintenance backend.
# ---------------------------------------------------------

class PredictionResponse(BaseModel):

    # Probability that the machine will fail
    failure_probability: float

    # Final failure prediction
    # True  -> failure predicted
    # False -> no failure predicted
    predicted_failure: bool

    # Raw anomaly score produced by the anomaly model
    anomaly_score: float

    # Position of the anomaly score compared with
    # the training/reference distribution
    anomaly_percentile: float

    # Whether the machine is considered anomalous
    is_anomaly: bool

    # Failure-mode probabilities produced by the
    # failure-mode model
    failure_modes: Dict[str, float]

    # Overall health status
    # Example: Normal, Warning, High, Critical
    health_status: str

    # Most likely failure mode, if one is identified
    failure_mode: Optional[str]

    # Human-readable failure mode name
    failure_mode_name: Optional[str]

    # Explanation of why the machine received
    # this prediction
    explanation: str

    # Recommended maintenance action
    maintenance_recommendation: str