"""
Failure Mode Model Test
-----------------------
Tests the custom FailureModeComponent supplied by the ML team.

Unlike a normal scikit-learn classifier, this component does
not have predict() or predict_proba() methods.

It provides a probabilities() method that returns the
probability produced by each available failure-mode model.
"""

import sys
from pathlib import Path

import joblib
import pandas as pd


# =========================================================
# 1. FIND PROJECT ROOT
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The serialized model depends on modules inside src/.
sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================
# 2. MODEL PATH
# =========================================================

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "failure_mode_pipeline.joblib"
)


# =========================================================
# 3. LOAD FAILURE-MODE MODEL
# =========================================================

print("Loading failure-mode model...")

mode_model = joblib.load(MODEL_PATH)

print("Failure-mode model loaded successfully!")
print("Model type:", type(mode_model))


# =========================================================
# 4. CREATE TEST INPUT
# =========================================================

sample = pd.DataFrame([
    {
        "product_type": "L",
        "air_temperature": 298.1,
        "process_temperature": 308.6,
        "rotational_speed": 1450,
        "torque": 45,
        "tool_wear": 120
    }
])


print("\nInput:")
print(sample)


# =========================================================
# 5. GET FAILURE-MODE PROBABILITIES
# =========================================================

# The custom FailureModeComponent provides a
# probabilities() method.
#
# It returns probabilities for the failure modes that have
# standalone models available.

print("\nCalculating failure-mode probabilities...")

probabilities = mode_model.probabilities(sample)


# =========================================================
# 6. DISPLAY RESULTS
# =========================================================

print("\nFailure-mode probabilities:")

for mode, values in probabilities.items():

    print(
        f"{mode}: {values[0]:.4f} "
        f"({values[0] * 100:.2f}%)"
    )


# =========================================================
# 7. DISPLAY AVAILABLE MODELS
# =========================================================

print("\nAvailable failure-mode models:")

for mode in mode_model.models_.keys():

    print(
        f"{mode} "
        f"(threshold = {mode_model.thresholds_[mode]:.4f})"
    )