"""
Anomaly Model Test
------------------
This file checks whether the supplied anomaly model can be
loaded and used with the same six inputs as the main model.

IMPORTANT:
The anomaly score is NOT a failure probability.

It tells us how unusual the machine's current operating
condition is compared with normal training conditions.
"""

import sys
from pathlib import Path

import joblib
import pandas as pd


# =========================================================
# 1. FIND PROJECT ROOT
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The anomaly model depends on modules inside src/.
sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================
# 2. MODEL PATH
# =========================================================

MODEL_PATH = PROJECT_ROOT / "models" / "anomaly_model.joblib"


# =========================================================
# 3. LOAD ANOMALY MODEL
# =========================================================

print("Loading anomaly model...")

anomaly_model = joblib.load(MODEL_PATH)

print("Anomaly model loaded successfully!")
print("Model type:", type(anomaly_model))


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
# 5. CALCULATE ANOMALY
# =========================================================

# The supplied AnomalyComponent has a score() method.
#
# It returns:
#
# raw_score
# percentile
# is_anomaly
#
# Higher percentile = more unusual compared with
# normal training examples.

raw_score, percentile, is_anomaly = anomaly_model.score(sample)


# =========================================================
# 6. DISPLAY RESULTS
# =========================================================

print("\nAnomaly results:")

print("Raw anomaly score:", raw_score[0])

print(
    "Anomaly percentile:",
    f"{percentile[0] * 100:.2f}%"
)

print("Is anomaly:", bool(is_anomaly[0]))