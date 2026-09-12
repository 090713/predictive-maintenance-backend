# schemas.py
# ---------------------------------------------------------
# This file defines the input and output formats of our API.
#
# MachineInput:
#   Data that the frontend sends to the backend.
#
# PredictionResponse:
#   Data that the backend sends back to the frontend.
#
# The response was extended to match the frontend integration
# contract. All original response fields are preserved so that
# existing clients keep working.
# ---------------------------------------------------------

from typing import Dict, List, Optional, Literal

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
# NESTED OUTPUT SCHEMAS
# ---------------------------------------------------------

class FailureModeDetail(BaseModel):
    """
    One entry in the likely-failure-modes list.

    Produced by the existing FailureModeComponent.rank().
    `probability` is only present when a standalone model
    exists for that mode; otherwise scoring uses `score`
    with the semantics described by `score_kind`.
    """

    # Failure-mode code: TWF, HDF, PWF, OSF or RNF
    mode: str

    # Human-readable failure-mode name
    name: str

    # Probability from the trained mode model (if one exists)
    probability: Optional[float] = None

    # Rank signal used to order the modes
    score: float

    # Explains what `score` actually means (never a fake value)
    score_kind: str

    # Whether the deterministic condition rule supports this mode
    supporting_condition: bool = False

    # Honest limitation note for this mode (if any)
    note: Optional[str] = None


class ContributingFeature(BaseModel):
    """
    One entry in the contributing-features list.

    NOT a SHAP value. These magnitudes are computed by
    leave-one-out replacement on the frozen model: each raw
    sensor value is replaced by its training median and the
    change in failure probability is measured. This is a real
    delta produced by the actual model.
    """

    # Canonical feature key (matches the model input naming)
    feature: str

    # Human-readable label for display
    label: str

    # The current input value for this feature
    value: float

    # Absolute change in failure probability when the feature
    # is moved to its training median
    magnitude: float

    # Whether the current value increases or decreases risk
    direction: Literal["increases", "decreases"]

    # Method used so consumers know this is not SHAP
    method: str = "leave_one_out_replacement_with_training_baseline"


# ---------------------------------------------------------
# OUTPUT SCHEMA
# ---------------------------------------------------------
# Combined response returned to the frontend.
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
    # the training/reference distribution.
    # IMPORTANT: returned as a fraction 0.0 - 1.0.
    # Multiply by 100 if your UI expects a 0 - 100 scale.
    anomaly_percentile: float

    # Whether the machine is considered anomalous
    is_anomaly: bool

    # Failure-mode probabilities produced by the
    # failure-mode model (only modes with standalone models)
    failure_modes: Dict[str, float]

    # Overall health status.
    # Values: Normal, Warning, High Risk, Critical
    health_status: str

    # Most likely failure mode, if one is identified
    failure_mode: Optional[str]

    # Human-readable failure mode name
    failure_mode_name: Optional[str]

    # Explanation of why the machine received
    # this prediction
    explanation: str

    # Recommended maintenance action (kept for compatibility)
    maintenance_recommendation: str

    # -------------------------------------------------------
    # EXTENDED FIELDS (frontend integration contract)
    # -------------------------------------------------------

    # Clean class label:
    # e.g. "HDF" when a mode is identified, otherwise
    # "NO FAILURE"/"FAILURE"
    predicted_class: str

    # Recommended maintenance action (frontend field name)
    recommended_maintenance_action: str

    # Operating decision threshold selected during validation
    decision_threshold: float

    # Policy label derived from the same probability bands
    # used for health_status: Low / Medium / High / Critical
    risk_level: str

    # Policy label derived from risk_level:
    # Routine / Scheduled / Urgent / Immediate
    urgency: str

    # Ranked failure-mode details (mode, name, probability,
    # score, score_kind, supporting_condition, note)
    likely_failure_modes: List[FailureModeDetail]

    # Per-feature contribution to the failure probability
    # (leave-one-out on the frozen model; not SHAP)
    contributing_features: List[ContributingFeature]

    # Human-readable trigger state for every deterministic
    # condition rule (from configs/condition rules)
    condition_evidence: List[str]

    # Trained model version identifier
    model_version: str

    # Unique identifier for this prediction
    prediction_id: str

    # UTC timestamp of when the prediction was made
    prediction_timestamp: str

    # Inference time in milliseconds
    latency_ms: float

    # Decision-support disclaimer
    decision_support_notice: str