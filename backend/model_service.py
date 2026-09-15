"""
Model Service
-------------
This file is responsible for loading the ML components
and combining their results.

The three ML components are:

1. Main failure prediction model
   -> Predicts overall machine failure probability.

2. Anomaly detection model
   -> Determines how unusual the current machine condition is.

3. Failure-mode model
   -> Estimates probabilities for supported failure modes
      such as HDF, PWF and OSF.
"""

import sys
from pathlib import Path

import joblib
import pandas as pd
import json

from backend.decision_service import (
    get_health_status,
    get_maintenance_action
)


# =========================================================
# 1. FIND PROJECT ROOT
# =========================================================

# This file is:
#
# Predictive-Maintenance-Agent/
# └── backend/
#     └── model_service.py
#
# Therefore .parent.parent gives us the project root.

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# =========================================================
# 2. MAKE src/ AVAILABLE
# =========================================================

# The saved Joblib models depend on Python modules inside
# our project's src/ directory.
#
# For example:
# src.feature_engineering
# src.anomaly_detection
# src.failure_mode_model
#
# Adding the project root allows Python to find those modules.

sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================
# 3. MODEL PATHS
# =========================================================

MAIN_MODEL_PATH = (
    PROJECT_ROOT / "models" / "model_pipeline.joblib"
)

ANOMALY_MODEL_PATH = (
    PROJECT_ROOT / "models" / "anomaly_model.joblib"
)

FAILURE_MODE_MODEL_PATH = (
    PROJECT_ROOT / "models" / "failure_mode_pipeline.joblib"
)


# =========================================================
# 4. LOAD MODELS
# =========================================================

print("Loading predictive maintenance models...")

# Overall failure prediction model
main_model = joblib.load(MAIN_MODEL_PATH)

# Anomaly detection component
anomaly_model = joblib.load(ANOMALY_MODEL_PATH)

# Failure-mode component
failure_mode_model = joblib.load(FAILURE_MODE_MODEL_PATH)

print("All predictive maintenance models loaded successfully!")

# ---------------------------------------------------------
# Load the decision threshold selected during model training.
#
# IMPORTANT:
# We should NOT automatically use model.predict() here,
# because the trained model has a custom operating threshold
# selected on validation data.
# ---------------------------------------------------------

THRESHOLD_PATH = PROJECT_ROOT / "models" / "threshold.json"

with open(THRESHOLD_PATH, "r") as file:
    threshold_config = json.load(file)

FAILURE_THRESHOLD = threshold_config["threshold"]

print(
    f"Failure decision threshold loaded: {FAILURE_THRESHOLD:.4f}"
)


# =========================================================
# 5. PREDICTION FUNCTION
# =========================================================

def predict_machine(
    product_type: str,
    air_temperature: float,
    process_temperature: float,
    rotational_speed: float,
    torque: float,
    tool_wear: float
):
    """
    Run all ML components and the decision layer
    for one machine.

    Flow:

        Machine data
             ↓
        ML predictions
             ↓
        Decision layer
             ↓
        Complete application result
    """

    # =====================================================
    # CREATE INPUT DATAFRAME
    # =====================================================

    input_data = pd.DataFrame([
        {
            "product_type": product_type,
            "air_temperature": air_temperature,
            "process_temperature": process_temperature,
            "rotational_speed": rotational_speed,
            "torque": torque,
            "tool_wear": tool_wear
        }
    ])


    # =====================================================
    # 1. OVERALL FAILURE PREDICTION
    # =====================================================

    probabilities = main_model.predict_proba(input_data)

    # Probability that the machine will fail
    failure_probability = float(probabilities[0][1])

    # ---------------------------------------------------------
    # The trained model uses a validation-selected threshold
    # instead of the default 0.50 threshold.
    # ---------------------------------------------------------
    predicted_failure = (
        failure_probability >= FAILURE_THRESHOLD
    )

    # =====================================================
    # 2. ANOMALY DETECTION
    # =====================================================

    raw_score, percentile, is_anomaly = anomaly_model.score(
        input_data
    )

    anomaly_score = float(raw_score[0])

    anomaly_percentile = float(percentile[0])

    is_anomalous = bool(is_anomaly[0])


    # =====================================================
    # 3. FAILURE-MODE PREDICTION
    # =====================================================

    mode_probabilities = failure_mode_model.probabilities(
        input_data
    )

    failure_modes = {}

    for mode, values in mode_probabilities.items():
        failure_modes[mode] = float(values[0])


    # =====================================================
    # 4. DETERMINE MACHINE HEALTH
    # =====================================================

    health_status = get_health_status(
        failure_probability
    )


    # =====================================================
    # 5. GENERATE EXPLANATION AND RECOMMENDATION
    # =====================================================

    maintenance_info = get_maintenance_action(
        failure_modes=failure_modes,
        predicted_failure=predicted_failure,
        tool_wear=tool_wear
    )


    # =====================================================
    # 6. COMBINE EVERYTHING
    # =====================================================

    return {
        # Overall prediction
        "failure_probability": failure_probability,
        "predicted_failure": predicted_failure,

        # Anomaly information
        "anomaly_score": anomaly_score,
        "anomaly_percentile": anomaly_percentile,
        "is_anomaly": is_anomalous,

        # Failure modes
        "failure_modes": failure_modes,

        # Decision layer
        "health_status": health_status,

        "failure_mode": (
            maintenance_info["failure_mode"]
        ),

        "failure_mode_name": (
            maintenance_info["failure_mode_name"]
        ),

        "explanation": (
            maintenance_info["explanation"]
        ),

        "maintenance_recommendation": (
            maintenance_info[
                "maintenance_recommendation"
            ]
        )
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    result = predict_machine(
        product_type="L",
        air_temperature=298.1,
        process_temperature=308.6,
        rotational_speed=1450,
        torque=45,
        tool_wear=120
    )

    print("\nCombined prediction result:")

    print(result)