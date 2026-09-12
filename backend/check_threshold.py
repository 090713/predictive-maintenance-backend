# check_threshold.py
# ---------------------------------------------------------
# This script checks the threshold and metadata supplied
# with the trained predictive-maintenance model.
#
# We are NOT changing the model.
# We are only checking which threshold the backend should use.
# ---------------------------------------------------------

import json


# ---------------------------------------------------------
# 1. Open the saved threshold configuration
# ---------------------------------------------------------

with open("models/threshold.json", "r") as file:
    threshold_data = json.load(file)


print("Threshold configuration:")
print(threshold_data)


# ---------------------------------------------------------
# 2. Open the model metadata
# ---------------------------------------------------------

with open("models/model_metadata.json", "r") as file:
    metadata = json.load(file)


print("\nModel metadata:")
print(metadata)