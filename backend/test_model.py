"""
Simple test to check whether the ML model can be loaded
and used by our backend project.
"""

import sys
from pathlib import Path

import joblib
import pandas as pd


# ---------------------------------------------------------
# Find the project root.
#
# __file__ points to:
# Predictive-Maintenance-Agent/backend/test_model.py
#
# .parent        -> backend
# .parent.parent -> Predictive-Maintenance-Agent
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Add the project root to Python's import path.
#
# This is important because the Joblib model depends on
# modules such as src.feature_engineering.
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------
# Model location
# ---------------------------------------------------------
MODEL_PATH = PROJECT_ROOT / "models" / "model_pipeline.joblib"


print("Loading model...")
print("Model path:", MODEL_PATH)


# ---------------------------------------------------------
# Load the trained pipeline
# ---------------------------------------------------------
model = joblib.load(MODEL_PATH)

print("Model loaded successfully!")
print("Model type:", type(model))


# ---------------------------------------------------------
# Create ONE sample using the exact six fields expected
# by the ML model.
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# Ask the model for the failure probability.
#
# predict_proba() returns:
# [probability of normal, probability of failure]
# ---------------------------------------------------------
probabilities = model.predict_proba(sample)

failure_probability = probabilities[0][1]

print("\nFailure probability:")
print(f"{failure_probability:.4f}")


# ---------------------------------------------------------
# Get the model's predicted class.
# ---------------------------------------------------------
prediction = model.predict(sample)[0]

print("\nPredicted class:")
print(prediction)